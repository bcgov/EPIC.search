import time
import threading
from datetime import datetime, timedelta
import os

class ProgressTracker:
    def __init__(self):
        self.start_time = None
        self.total_projects = 0
        self.total_documents = 0
        self.processed_projects = 0
        self.processed_documents = 0
        self.failed_documents = 0
        self.skipped_documents = 0
        self.current_project_ids = []  # Track project IDs for this run
        self.start_processing_log_id = None  # Track the highest ID before run starts
        self.is_retry_mode = False  # Track if this is a retry operation
        self.retry_document_ids = set()  # Track specific document IDs being retried
        self.current_project_name = ""
        self.active_documents = {}  # dict of {worker_id: {name, pages, size_mb}}
        self.total_pages_processed = 0
        self.total_size_mb_processed = 0.0
        self.last_summary_time = time.time()
        self.lock = threading.Lock()
        self._stop_logging = False
        
    def start(self, total_projects, total_documents, project_ids=None, is_retry_mode=False, retry_document_ids=None, timed_mode=False, time_limit_minutes=None):
        """Initialize progress tracking"""
        with self.lock:
            self.start_time = datetime.now()
            self.total_projects = total_projects
            self.total_documents = total_documents
            self.current_project_ids = project_ids or []
            self.is_retry_mode = is_retry_mode
            self.retry_document_ids = set(retry_document_ids or [])
            self.timed_mode = timed_mode
            self.time_limit_minutes = time_limit_minutes
            
            if not self.is_retry_mode:
                # For normal mode, get the highest processing log ID before we start
                try:
                    from src.models.pgvector.vector_models import ProcessingLog
                    from src.models import get_session
                    from sqlalchemy import func
                    
                    session = get_session()
                    max_id_result = session.query(func.max(ProcessingLog.id)).scalar()
                    self.start_processing_log_id = max_id_result or 0
                    session.close()
                    print(f"[DEBUG] Progress tracker starting - baseline processing log ID: {self.start_processing_log_id}")
                except Exception as e:
                    print(f"[WARN] Could not get baseline processing log ID: {e}")
                    self.start_processing_log_id = 0
            else:
                # For retry mode, we'll filter by document IDs and latest updates
                self.start_processing_log_id = None
                print(f"[DEBUG] Progress tracker starting in retry mode - tracking {len(self.retry_document_ids)} document IDs")
                
            self.processed_projects = 0
            self.processed_documents = 0
            self.failed_documents = 0
            self.skipped_documents = 0
            self.active_documents = {}
            self._stop_logging = False
            
        print(f"\n{'='*80}")
        print(f"EMBEDDER STARTED: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"SCOPE: {total_projects} projects, {total_documents} documents")
        print(f"CONCURRENCY: FILES={os.getenv('FILES_CONCURRENCY_SIZE', 'auto')}, "
              f"DB_POOL={os.getenv('DB_POOL_SIZE', 'auto')}/{os.getenv('DB_MAX_OVERFLOW', 'auto')}")
        print(f"{'='*80}\n")
        
        # Start background summary logging
        self.summary_thread = threading.Thread(target=self._periodic_summary, daemon=True)
        self.summary_thread.start()
    
    def update_current_project(self, project_name):
        """Update current project being processed"""
        with self.lock:
            self.current_project_name = project_name
    
    def start_document_processing(self, worker_id, document_name, pages=None, size_mb=None):
        """Register that a worker started processing a document"""
        with self.lock:
            # Calculate dynamic timeout based on document size
            timeout_minutes = self._calculate_dynamic_timeout(pages)
            
            self.active_documents[worker_id] = {
                'name': document_name,
                'pages': pages,
                'size_mb': size_mb,
                'start_time': time.time(),
                'timeout_minutes': timeout_minutes,
                'timeout_seconds': timeout_minutes * 60
            }
    
    def _calculate_dynamic_timeout(self, pages):
        """
        Calculate dynamic timeout based on document pages.
        
        Formula:
        - Base: 30 minutes for any document
        - Per-page: 2 minutes per page
        - Min: 30 minutes (for small/unknown docs)
        - Max: 240 minutes (4 hours safety cap)
        
        Args:
            pages (int or None): Number of pages in document
            
        Returns:
            int: Timeout in minutes
        """
        base_timeout = 30  # 30 minutes base
        per_page_timeout = 2  # 2 minutes per page
        max_timeout = 240  # 4 hours max
        min_timeout = 30  # 30 minutes min
        
        if pages and pages > 0:
            calculated_timeout = base_timeout + (pages * per_page_timeout)
            return min(max(calculated_timeout, min_timeout), max_timeout)
        else:
            # Unknown page count - use conservative default
            return min_timeout
    
    def finish_document_processing(self, worker_id, success=True, skipped=False, pages=None, size_mb=None):
        """Register that a worker finished processing a document"""
        with self.lock:
            # Remove from active documents
            if worker_id in self.active_documents:
                del self.active_documents[worker_id]
            
            # Update counters
            if success:
                self.processed_documents += 1
                # Add to totals if we have the info
                if pages is not None:
                    self.total_pages_processed += pages
                if size_mb is not None:
                    self.total_size_mb_processed += size_mb
            elif skipped:
                self.skipped_documents += 1
            else:
                self.failed_documents += 1
    
    def increment_processed(self):
        """Increment processed document count"""
        with self.lock:
            self.processed_documents += 1
    
    def increment_failed(self):
        """Increment failed document count"""
        with self.lock:
            self.failed_documents += 1
    
    def increment_skipped(self):
        """Increment skipped document count"""
        with self.lock:
            self.skipped_documents += 1
    
    def finish_project(self):
        """Mark a project as completed"""
        with self.lock:
            self.processed_projects += 1
    
    def force_cleanup_phantom_workers(self, max_hours=None):
        """
        Force cleanup of workers that have exceeded their dynamic timeouts.
        Uses document-specific timeouts instead of a fixed global timeout.
        
        Args:
            max_hours (int, optional): Legacy parameter - ignored in favor of dynamic timeouts
            
        Returns:
            int: Number of phantom workers cleaned up
        """
        with self.lock:
            if not self.active_documents:
                return 0
            
            current_time = time.time()
            phantom_workers = []
            
            for worker_id, doc_info in list(self.active_documents.items()):
                start_time = doc_info.get('start_time', current_time)
                processing_seconds = current_time - start_time
                
                # Get document-specific timeout
                timeout_seconds = doc_info.get('timeout_seconds', 1800)  # 30min default
                timeout_minutes = doc_info.get('timeout_minutes', 30)
                
                if processing_seconds > timeout_seconds:
                    phantom_workers.append(worker_id)
                    doc_name = doc_info.get('name', 'unknown')
                    overtime_minutes = (processing_seconds / 60) - timeout_minutes
                    pages = doc_info.get('pages', 'unknown')
                    
                    print(f"[CLEANUP] Removing worker {worker_id} stuck on {doc_name} ({pages}p) - {overtime_minutes:.0f}m over {timeout_minutes}m limit")
                    
                    # Remove from active documents
                    del self.active_documents[worker_id]
                    # Count as failed since it was stuck
                    self.failed_documents += 1
            
            if phantom_workers:
                print(f"[CLEANUP] Removed {len(phantom_workers)} phantom workers using dynamic timeouts")
            
            return len(phantom_workers)

    def stop(self, reason="Completed"):
        """Stop progress tracking and print final summary"""
        with self.lock:
            self._stop_logging = True
            
        # Force cleanup any remaining phantom workers before final summary
        phantom_count = self.force_cleanup_phantom_workers(max_hours=1)  # More aggressive cleanup at shutdown
        if phantom_count > 0:
            print(f"[CLEANUP] Cleaned {phantom_count} phantom workers during shutdown")
            
        if self.start_time:
            self._print_final_summary(reason)
    
    def _periodic_summary(self):
        """Print summary every 30 seconds"""
        while not self._stop_logging:
            time.sleep(30)  # Summary every 30 seconds
            if not self._stop_logging:
                self._print_summary()
    
    def _print_summary(self):
        """Print current progress summary"""
        with self.lock:
            if not self.start_time:
                return
                
            elapsed = datetime.now() - self.start_time
            
            # Get accurate counts from database for real-time reporting
            try:
                from src.models.pgvector.vector_models import ProcessingLog
                from src.models import get_session
                
                session = get_session()
                
                if self.is_retry_mode:
                    # For retry mode, filter by specific document IDs and get latest status
                    if self.retry_document_ids:
                        # Get the latest status for each retry document
                        from sqlalchemy import func
                        
                        # Query for the latest processing log for each document being retried
                        subquery = session.query(
                            ProcessingLog.document_id,
                            func.max(ProcessingLog.processed_at).label('max_processed_at')
                        ).filter(
                            ProcessingLog.document_id.in_(self.retry_document_ids)
                        ).group_by(ProcessingLog.document_id).subquery()
                        
                        # Join to get the actual records with latest processed_at
                        query = session.query(ProcessingLog).join(
                            subquery,
                            (ProcessingLog.document_id == subquery.c.document_id) &
                            (ProcessingLog.processed_at == subquery.c.max_processed_at)
                        )
                        
                        # Additional project filtering if available
                        if self.current_project_ids:
                            query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
                    else:
                        # No specific document IDs, fall back to project-based filtering with recent timestamp
                        query = session.query(ProcessingLog)
                        if self.current_project_ids:
                            query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
                        # For retry mode without specific doc IDs, look for records updated during this run
                        query = query.filter(ProcessingLog.processed_at >= self.start_time)
                else:
                    # Normal mode: filter by ID - only records created during this run
                    query = session.query(ProcessingLog)
                    
                    # Filter by ID - only records created during this run
                    if self.start_processing_log_id is not None:
                        query = query.filter(ProcessingLog.id > self.start_processing_log_id)
                    
                    # If we have specific project IDs, filter by them for additional accuracy
                    if self.current_project_ids:
                        query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
                
                # Get actual counts from database for this run only
                success_count = query.filter(ProcessingLog.status == 'success').count()
                failure_count = query.filter(ProcessingLog.status == 'failure').count()
                skipped_count = query.filter(ProcessingLog.status == 'skipped').count()
                total_processed = success_count + failure_count + skipped_count
                session.close()
                
            except Exception as e:
                # Fallback to progress tracker internal counters if database query fails
                print(f"[WARN] Could not get database counts for progress summary: {e}")
                success_count = self.processed_documents
                failure_count = self.failed_documents
                skipped_count = self.skipped_documents
                total_processed = success_count + failure_count + skipped_count
            
            # Calculate rates
            if elapsed.total_seconds() > 0:
                docs_per_hour = (total_processed / elapsed.total_seconds()) * 3600
                if total_processed > 0:
                    eta_seconds = (self.total_documents - total_processed) / (total_processed / elapsed.total_seconds())
                    eta = timedelta(seconds=int(eta_seconds))
                else:
                    eta = "Unknown"
            else:
                docs_per_hour = 0
                eta = "Unknown"
            
            # Progress percentages
            project_pct = (self.processed_projects / max(1, self.total_projects)) * 100
            doc_pct = (total_processed / max(1, self.total_documents)) * 100
            
            print(f"\n{'-'*80}")
            print(f"PROGRESS SUMMARY - {datetime.now().strftime('%H:%M:%S')}")
            
            # Show timed mode info if applicable
            if getattr(self, 'timed_mode', False) and getattr(self, 'time_limit_minutes', None):
                elapsed_minutes = elapsed.total_seconds() / 60
                remaining_minutes = max(0, self.time_limit_minutes - elapsed_minutes)
                print(f"Runtime: {str(elapsed).split('.')[0]} [TIMED MODE: {self.time_limit_minutes}m limit, {remaining_minutes:.1f}m remaining]")
            else:
                print(f"Runtime: {str(elapsed).split('.')[0]}")
                
            print(f"Projects: {self.processed_projects}/{self.total_projects} ({project_pct:.1f}%)")
            print(f"Documents: {total_processed}/{self.total_documents} ({doc_pct:.1f}%) "
                  f"[Success: {success_count}, Failed: {failure_count}, Skipped: {skipped_count}]")
            
            # Add throughput metrics if we have data
            throughput_info = ""
            if self.total_pages_processed > 0:
                pages_per_hour = (self.total_pages_processed / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
                throughput_info += f" | Pages: {self.total_pages_processed:,} ({pages_per_hour:.0f}/hr)"
            
            if self.total_size_mb_processed > 0:
                mb_per_hour = (self.total_size_mb_processed / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
                throughput_info += f" | Data: {self.total_size_mb_processed:.1f} MB ({mb_per_hour:.1f} MB/hr)"
            
            print(f"Rate: {docs_per_hour:.1f} docs/hour{throughput_info} | ETA: {eta}")
            if self.current_project_name:
                print(f"Current Project: {self.current_project_name}")
            
            # Show currently active documents
            if self.active_documents:
                print(f"Active Workers ({len(self.active_documents)}):")
                current_time = time.time()
                phantom_workers = []
                
                for i, (worker_id, doc_info) in enumerate(self.active_documents.items(), 1):
                    doc_name = doc_info['name']
                    # Document name is already truncated in processor.py, no need to truncate again
                    display_name = doc_name
                    
                    # Calculate processing time
                    start_time = doc_info.get('start_time', current_time)
                    processing_seconds = int(current_time - start_time)
                    processing_minutes = processing_seconds / 60
                    
                    # Get dynamic timeout for this document
                    timeout_seconds = doc_info.get('timeout_seconds', 7200)  # Default 2h fallback
                    timeout_minutes = doc_info.get('timeout_minutes', 120)  # Default 2h fallback
                    
                    # Check if worker exceeded its dynamic timeout
                    is_stuck = processing_seconds > timeout_seconds
                    if is_stuck:
                        phantom_workers.append((worker_id, processing_seconds, doc_name, timeout_minutes))
                    
                    # Add page count, size info, and timeout info if available
                    extra_info = ""
                    has_page_info = doc_info.get('pages') is not None
                    has_size_info = doc_info.get('size_mb') is not None
                    
                    if has_page_info:
                        extra_info += f" ({doc_info['pages']}p"
                        if has_size_info:
                            extra_info += f", {doc_info['size_mb']:.1f}MB"
                        extra_info += f", {processing_seconds}s, timeout:{timeout_minutes}m)"
                    elif has_size_info:
                        extra_info += f" ({doc_info['size_mb']:.1f}MB, {processing_seconds}s, timeout:{timeout_minutes}m)"
                    else:
                        # No size or page info available
                        extra_info += f" ({processing_seconds}s, timeout:{timeout_minutes}m)"
                    
                    # Mark workers with dynamic timeout warning
                    if is_stuck:
                        overtime_minutes = processing_minutes - timeout_minutes
                        warning = f" [STUCK - {overtime_minutes:.0f}m OVER {timeout_minutes}m LIMIT]"
                    elif processing_seconds > (timeout_seconds * 0.8):  # Warning at 80% of timeout
                        remaining_minutes = (timeout_seconds - processing_seconds) / 60
                        warning = f" [WARNING - {remaining_minutes:.0f}m until timeout]"
                    else:
                        warning = ""
                    
                    print(f"  [{i}] Worker-{worker_id}: {display_name}{extra_info}{warning}")
                
                # Report phantom workers with dynamic timeout info
                if phantom_workers:
                    print(f"[WARN] Detected {len(phantom_workers)} workers exceeded their dynamic timeouts:")
                    for worker_id, seconds, doc_name, timeout_mins in phantom_workers:
                        overtime_mins = (seconds / 60) - timeout_mins
                        print(f"[WARN]   Worker-{worker_id}: {doc_name} ({overtime_mins:.0f}m over {timeout_mins}m limit)")
            else:
                print("Active Workers: None (waiting for documents)")
            print(f"{'-'*80}")
    
    def _print_final_summary(self, reason="Completed"):
        """Print final completion summary"""
        elapsed = datetime.now() - self.start_time
        total_processed_this_run = self.processed_documents + self.failed_documents + self.skipped_documents
        docs_per_hour = (total_processed_this_run / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"EMBEDDER COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Runtime: {str(elapsed).split('.')[0]}")
        print(f"Final Results:")
        print(f"   Projects: {self.processed_projects}/{self.total_projects}")
        
        # Always get actual counts from database for accuracy
        try:
            from src.models.pgvector.vector_models import ProcessingLog
            from src.models import get_session
            
            session = get_session()
            
            if self.is_retry_mode:
                # For retry mode, filter by specific document IDs and get latest status
                if self.retry_document_ids:
                    # Get the latest status for each retry document
                    from sqlalchemy import func
                    
                    # Query for the latest processing log for each document being retried
                    subquery = session.query(
                        ProcessingLog.document_id,
                        func.max(ProcessingLog.processed_at).label('max_processed_at')
                    ).filter(
                        ProcessingLog.document_id.in_(self.retry_document_ids)
                    ).group_by(ProcessingLog.document_id).subquery()
                    
                    # Join to get the actual records with latest processed_at
                    query = session.query(ProcessingLog).join(
                        subquery,
                        (ProcessingLog.document_id == subquery.c.document_id) &
                        (ProcessingLog.processed_at == subquery.c.max_processed_at)
                    )
                    
                    # Additional project filtering if available
                    if self.current_project_ids:
                        query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
                else:
                    # No specific document IDs, fall back to project-based filtering with recent timestamp
                    query = session.query(ProcessingLog)
                    if self.current_project_ids:
                        query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
                    # For retry mode without specific doc IDs, look for records updated during this run
                    query = query.filter(ProcessingLog.processed_at >= self.start_time)
            else:
                # Normal mode: filter by ID - only records created during this run
                query = session.query(ProcessingLog)
                
                # Filter by ID - only records created during this run
                if self.start_processing_log_id is not None:
                    query = query.filter(ProcessingLog.id > self.start_processing_log_id)
                
                # If we have specific project IDs, filter by them for additional accuracy
                if self.current_project_ids:
                    query = query.filter(ProcessingLog.project_id.in_(self.current_project_ids))
            
            # Get actual counts from database for this run only
            success_count = query.filter(ProcessingLog.status == 'success').count()
            failure_count = query.filter(ProcessingLog.status == 'failure').count()
            skipped_count = query.filter(ProcessingLog.status == 'skipped').count()
            actual_total = success_count + failure_count + skipped_count
            session.close()
            
            # Show documents processed vs queued
            if actual_total < self.total_documents and reason != "Completed":
                print(f"   Documents: {actual_total}/{actual_total} (of {self.total_documents} queued, stopped early due to {reason.lower()})")
            else:
                print(f"   Documents: {actual_total}/{self.total_documents}")
            
            print(f"   Successful: {success_count}")
            print(f"   Failed: {failure_count}")
            print(f"   Skipped: {skipped_count}")
            
            # Show note if database counts differ from progress tracker counts
            if (success_count != self.processed_documents or 
                failure_count != self.failed_documents or 
                skipped_count != self.skipped_documents):
                if self.is_retry_mode:
                    print(f"   Note: Counts from database for retry operation (progress tracker: {self.processed_documents}S/{self.failed_documents}F/{self.skipped_documents}Sk)")
                else:
                    print(f"   Note: Counts from database since ID > {self.start_processing_log_id} (progress tracker: {self.processed_documents}S/{self.failed_documents}F/{self.skipped_documents}Sk)")
                
        except Exception as db_err:
            print(f"   Note: Could not get database counts: {db_err}")
            # Fallback to progress tracker counts
            if total_processed_this_run < self.total_documents and reason != "Completed":
                print(f"   Documents: {total_processed_this_run}/{total_processed_this_run} (of {self.total_documents} queued, stopped early due to {reason.lower()})")
            else:
                print(f"   Documents: {total_processed_this_run}/{self.total_documents}")
            
            print(f"   Successful: {self.processed_documents}")
            print(f"   Failed: {self.failed_documents}")
            print(f"   Skipped: {self.skipped_documents}")
        
        if self.total_pages_processed > 0:
            print(f"   Pages Processed: {self.total_pages_processed:,}")
        if self.total_size_mb_processed > 0:
            print(f"   Data Processed: {self.total_size_mb_processed:.1f} MB")
        print(f"Average Rate: {docs_per_hour:.1f} documents/hour")
        if reason != "Completed":
            print(f"REASON: {reason}")
        print(f"{'='*80}\n")

# Global progress tracker instance
progress_tracker = ProgressTracker()
