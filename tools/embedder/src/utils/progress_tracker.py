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
        self.current_project_name = ""
        self.active_documents = {}  # dict of {worker_id: {name, pages, size_mb}}
        self.total_pages_processed = 0
        self.total_size_mb_processed = 0.0
        self.last_summary_time = time.time()
        self.lock = threading.Lock()
        self._stop_logging = False
        
    def start(self, total_projects, total_documents):
        """Initialize progress tracking"""
        with self.lock:
            self.start_time = datetime.now()
            self.total_projects = total_projects
            self.total_documents = total_documents
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
            self.active_documents[worker_id] = {
                'name': document_name,
                'pages': pages,
                'size_mb': size_mb
            }
    
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
    
    def stop(self, reason="Completed"):
        """Stop progress tracking and print final summary"""
        with self.lock:
            self._stop_logging = True
            
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
            total_processed = self.processed_documents + self.failed_documents + self.skipped_documents
            
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
            print(f"Runtime: {str(elapsed).split('.')[0]}")
            print(f"Projects: {self.processed_projects}/{self.total_projects} ({project_pct:.1f}%)")
            print(f"Documents: {total_processed}/{self.total_documents} ({doc_pct:.1f}%) "
                  f"[Success: {self.processed_documents}, Failed: {self.failed_documents}, Skipped: {self.skipped_documents}]")
            
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
                for i, (worker_id, doc_info) in enumerate(self.active_documents.items(), 1):
                    doc_name = doc_info['name']
                    # Document name is already truncated in processor.py, no need to truncate again
                    display_name = doc_name
                    
                    # Add page count and size info if available
                    extra_info = ""
                    has_page_info = doc_info.get('pages') is not None
                    has_size_info = doc_info.get('size_mb') is not None
                    
                    if has_page_info:
                        extra_info += f" ({doc_info['pages']}p"
                        if has_size_info:
                            extra_info += f", {doc_info['size_mb']:.1f}MB)"
                        else:
                            extra_info += ")"
                    elif has_size_info:
                        extra_info += f" ({doc_info['size_mb']:.1f}MB)"
                    else:
                        # No size or page info available
                        extra_info += " (processing...)"
                    
                    print(f"  [{i}] Worker-{worker_id}: {display_name}{extra_info}")
            else:
                print("Active Workers: None (waiting for documents)")
            print(f"{'-'*80}")
    
    def _print_final_summary(self, reason="Completed"):
        """Print final completion summary"""
        elapsed = datetime.now() - self.start_time
        total_processed = self.processed_documents + self.failed_documents + self.skipped_documents
        docs_per_hour = (total_processed / elapsed.total_seconds()) * 3600 if elapsed.total_seconds() > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"EMBEDDER COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Runtime: {str(elapsed).split('.')[0]}")
        print(f"Final Results:")
        print(f"   Projects: {self.processed_projects}/{self.total_projects}")
        print(f"   Documents: {total_processed}/{self.total_documents}")
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
