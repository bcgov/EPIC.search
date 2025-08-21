import os
from concurrent.futures import ProcessPoolExecutor, as_completed, wait, FIRST_COMPLETED
from concurrent.futures.process import BrokenProcessPool

from .logger import log_processing_result
from .loader import load_data
from src.utils.progress_tracker import progress_tracker

def process_mixed_project_files(document_tasks, file_keys, metadata_list, api_docs_list, batch_size=4, temp_dir=None, is_retry=False, timed_mode=False, time_limit_seconds=None, start_time=None, max_pages=None):
    """
    Process files from multiple projects concurrently using a unified worker pool with dynamic queuing.
    Workers continuously pull new documents as they finish, maximizing CPU utilization.
    
    Args:
        document_tasks (list): List of DocumentTask namedtuples containing project info for each document
        file_keys (list): List of file keys or paths to be processed
        metadata_list (list): List of metadata dictionaries corresponding to each file  
        api_docs_list (list): List of API document objects corresponding to each file
        batch_size (int, optional): Number of worker processes to run in parallel. Defaults to 4.
        temp_dir (str, optional): Temporary directory for processing files. Passed to load_data.
        is_retry (bool, optional): If True, cleanup existing document content before processing.
        timed_mode (bool, optional): If True, check time limits and stop gracefully when reached.
        time_limit_seconds (int, optional): Time limit in seconds for timed mode.
        start_time (datetime, optional): Start time for timed mode calculations.
        max_pages (int, optional): Skip documents with more than this many pages to avoid threading/memory issues.
        
    Returns:
        dict: Processing results including time_limit_reached status
    """
    from datetime import datetime
    from src.config.settings import get_settings
    
    settings = get_settings()
    
    if len(file_keys) != len(metadata_list) or len(file_keys) != len(api_docs_list) or len(file_keys) != len(document_tasks):
        raise ValueError("document_tasks, file_keys, metadata_list, and api_docs_list must have the same length.")

    if not file_keys:
        print("No files to process.")
        return {"time_limit_reached": False, "documents_processed": 0}

    print(f"Starting ProcessPoolExecutor with max_workers={batch_size}")
    print(f"DYNAMIC QUEUING: Workers will continuously pull new documents as they finish")
    
    if timed_mode and time_limit_seconds and start_time:
        print(f"TIMED MODE: Will stop gracefully when {time_limit_seconds/60:.1f} minute limit is reached")
    
    time_limit_reached = False
    documents_processed = 0
    
    # Determine project mode for progress tracking
    if len(set(task.project_name for task in document_tasks)) > 1:
        progress_tracker.update_current_project("Cross-Project Processing")
        print(f"[PROGRESS] Set project mode: Cross-Project Processing ({len(set(task.project_name for task in document_tasks))} projects)")
    else:
        # Single project mode
        single_project_name = document_tasks[0].project_name if document_tasks else "Unknown Project"
        progress_tracker.update_current_project(single_project_name)
        print(f"[PROGRESS] Set project mode: {single_project_name}")
    
    with ProcessPoolExecutor(max_workers=batch_size) as executor:
        future_to_task = {}
        document_index = 0
        total_documents = len(document_tasks)
        completed_count = 0
        
        # Submit initial worker pool (up to worker_count workers)
        while document_index < min(batch_size, total_documents):
            # Check time limit before submitting initial work
            if timed_mode and time_limit_seconds and start_time:
                elapsed_time = datetime.now() - start_time
                if elapsed_time.total_seconds() >= time_limit_seconds:
                    print(f"[TIMED MODE] Time limit reached before processing could begin. Stopping gracefully.")
                    time_limit_reached = True
                    break
            
            task = document_tasks[document_index]
            file_key = file_keys[document_index]
            base_meta = metadata_list[document_index]
            api_doc = api_docs_list[document_index]
            
            worker_id = document_index % batch_size + 1
            doc_id = base_meta.get("document_id") or os.path.basename(file_key)
            doc_name = api_doc.get('name', doc_id)
            
            # File size handling with fallbacks and debug info
            file_size_raw = api_doc.get('internalSize', '0') or api_doc.get('fileSize', '0')
            try:
                file_size_bytes = int(file_size_raw) if file_size_raw else 0
            except (ValueError, TypeError):
                file_size_bytes = 0
                if settings.multi_processing_settings.debug_file_size_issues:
                    print(f"[DEBUG] Invalid file size for {doc_name}: internalSize='{api_doc.get('internalSize')}', fileSize='{api_doc.get('fileSize')}'")
            
            # Calculate size and pages with better defaults
            if file_size_bytes > 0:
                size_mb = file_size_bytes / (1024 * 1024)
                estimated_pages = max(1, int(file_size_bytes / 50000))  # ~50KB per page estimate
            else:
                # Fallback when size is unknown - use conservative estimates for display
                size_mb = None
                estimated_pages = None
                if file_size_bytes == 0 and settings.multi_processing_settings.debug_file_size_issues:
                    print(f"[DEBUG] No file size info for {doc_name}, will show as processing without size/page info")
            
            # Submit work and track it
            future = executor.submit(load_data, file_key, base_meta, temp_dir, api_doc, is_retry, max_pages)
            future_to_task[future] = (task, file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb, document_index)
            
            # Update progress tracker (no need to update current_project repeatedly in cross-project mode)
            progress_tracker.start_document_processing(worker_id, doc_name, estimated_pages, size_mb)
            
            document_index += 1
        
        if not time_limit_reached:
            print(f"Submitted initial {len(future_to_task)} documents to workers. Queue contains {total_documents - document_index} more documents.")
        
        # Process completed tasks and dynamically submit new work
        # Note: as_completed() only sees the initial futures, so we need to track new ones separately
        all_futures = set(future_to_task.keys())  # Track all futures (initial + dynamically added)
        process_pool_broken = False
        
        while all_futures and not process_pool_broken:
            # Wait for any future to complete
            try:
                done_futures, _ = wait(all_futures, return_when=FIRST_COMPLETED)
            except Exception as wait_error:
                print(f"[ERROR] Error waiting for futures: {wait_error}")
                print(f"[ERROR] Process pool may be broken. Stopping processing.")
                process_pool_broken = True
                break
            
            for future in done_futures:
                task, file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb, doc_index = future_to_task[future]
                doc_id = base_meta.get("document_id") or os.path.basename(file_key)
                project_id = task.project_id
                
                try:
                    result = future.result()
                    
                    if result is None:
                        # When result is None, check database to see if it was actually successful
                        # This can happen when documents are processed but return None due to early logging
                        try:
                            from src.schemas.processing_logs import ProcessingLog
                            from src.models.pgvector.vector_db_utils import get_database_session
                            
                            session = get_database_session()
                            log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
                            session.close()
                            
                            if log and log.status == "success":
                                print(f"[{completed_count + 1}/{total_documents}] File {doc_id} processing completed successfully (confirmed from database).")
                                progress_tracker.finish_document_processing(worker_id, success=True, pages=estimated_pages, size_mb=size_mb)
                            elif log and log.status == "skipped":
                                print(f"[{completed_count + 1}/{total_documents}] File {doc_id} processing skipped (confirmed from database).")
                                progress_tracker.finish_document_processing(worker_id, success=False, skipped=True)
                            else:
                                print(f"[{completed_count + 1}/{total_documents}] File {doc_id} processing completed with None result (status already logged internally).")
                                progress_tracker.finish_document_processing(worker_id, success=False, skipped=True)
                        except Exception as db_check_err:
                            print(f"[WARN] Could not verify database status for {doc_id}: {db_check_err}")
                            print(f"[{completed_count + 1}/{total_documents}] File {doc_id} processing completed with None result (status already logged internally).")
                            progress_tracker.finish_document_processing(worker_id, success=False, skipped=True)
                    else:
                        print(f"[{completed_count + 1}/{total_documents}] Successfully processed: {result}")
                        log_processing_result(project_id, doc_id, "success")
                        progress_tracker.finish_document_processing(worker_id, success=True, pages=estimated_pages, size_mb=size_mb)
                        
                except BrokenProcessPool as bpp_error:
                    print(f"[{completed_count + 1}/{total_documents}] CRITICAL: Process pool broken while processing {doc_id}: {bpp_error}")
                    print(f"[CRITICAL] A worker process crashed. Stopping all processing to prevent data corruption.")
                    log_processing_result(project_id, doc_id, "failure")
                    progress_tracker.finish_document_processing(worker_id, success=False, skipped=False)
                    # Remove this future and stop processing to prevent further corruption
                    all_futures.remove(future)
                    del future_to_task[future]
                    process_pool_broken = True
                    break  # Break out of the done_futures loop and stop processing
                except Exception as e:
                    print(f"[{completed_count + 1}/{total_documents}] Failed to process {doc_id}: {e}")
                    log_processing_result(project_id, doc_id, "failure")
                    progress_tracker.finish_document_processing(worker_id, success=False, skipped=False)
                    
                completed_count += 1
                documents_processed += 1
                
                # Remove completed future from tracking
                all_futures.remove(future)
                del future_to_task[future]
            
            # Check time limit after each document completes
            if timed_mode and time_limit_seconds and start_time:
                elapsed_time = datetime.now() - start_time
                elapsed_minutes = elapsed_time.total_seconds() / 60
                remaining_seconds = max(0, time_limit_seconds - elapsed_time.total_seconds())
                remaining_minutes = remaining_seconds / 60
                
                if elapsed_time.total_seconds() >= time_limit_seconds:
                    print(f"[TIMED MODE] Time limit of {time_limit_seconds/60:.1f} minutes reached after processing {completed_count} documents.")
                    print(f"[TIMED MODE] Elapsed: {elapsed_minutes:.1f}min. Stopping gracefully.")
                    print(f"[TIMED MODE] Cancelling remaining {total_documents - completed_count} documents in queue.")
                    time_limit_reached = True
                    
                    # Cancel any remaining futures that haven't started yet
                    for remaining_future in future_to_task:
                        if not remaining_future.done():
                            remaining_future.cancel()
                    
                    break
                
                # Show time status every 10 documents
                if completed_count % 10 == 0:
                    print(f"[TIMED MODE] Elapsed: {elapsed_minutes:.1f}min, Remaining: {remaining_minutes:.1f}min ({completed_count}/{total_documents} processed)")
            
            # DYNAMIC QUEUING: Only submit next document if time limit not reached and process pool is healthy
            if not time_limit_reached and not process_pool_broken and document_index < total_documents:
                # Final time check before submitting new work
                if timed_mode and time_limit_seconds and start_time:
                    elapsed_time = datetime.now() - start_time
                    if elapsed_time.total_seconds() >= time_limit_seconds:
                        print(f"[TIMED MODE] Time limit reached. Not submitting additional documents.")
                        time_limit_reached = True
                        break
                
                next_task = document_tasks[document_index]
                next_file_key = file_keys[document_index]
                next_base_meta = metadata_list[document_index]
                next_api_doc = api_docs_list[document_index]
                
                next_doc_id = next_base_meta.get("document_id") or os.path.basename(next_file_key)
                next_doc_name = next_api_doc.get('name', next_doc_id)
                
                # File size handling for next document with fallbacks and debug info
                next_file_size_raw = next_api_doc.get('internalSize', '0') or next_api_doc.get('fileSize', '0')
                try:
                    next_file_size_bytes = int(next_file_size_raw) if next_file_size_raw else 0
                except (ValueError, TypeError):
                    next_file_size_bytes = 0
                    if settings.multi_processing_settings.debug_file_size_issues:
                        print(f"[DEBUG] Invalid file size for {next_doc_name}: internalSize='{next_api_doc.get('internalSize')}', fileSize='{next_api_doc.get('fileSize')}'")
                
                # Calculate size and pages for next document
                if next_file_size_bytes > 0:
                    next_size_mb = next_file_size_bytes / (1024 * 1024)
                    next_estimated_pages = max(1, int(next_file_size_bytes / 50000))
                else:
                    next_size_mb = None
                    next_estimated_pages = None
                    if next_file_size_bytes == 0 and settings.multi_processing_settings.debug_file_size_issues:
                        print(f"[DEBUG] No file size info for {next_doc_name}, will show as processing without size/page info")
                
                # Submit next document immediately 
                try:
                    next_future = executor.submit(load_data, next_file_key, next_base_meta, temp_dir, next_api_doc, is_retry, max_pages)
                    future_to_task[next_future] = (next_task, next_file_key, next_base_meta, next_api_doc, worker_id, next_doc_name, next_estimated_pages, next_size_mb, document_index)
                    
                    # Add new future to tracking set for dynamic queuing
                    all_futures.add(next_future)
                    
                    # Update progress tracker for new document (no need to update current_project repeatedly)
                    progress_tracker.start_document_processing(worker_id, next_doc_name, next_estimated_pages, next_size_mb)
                    
                    print(f"[DYNAMIC] Worker {worker_id} immediately started next document: {next_doc_name} ({document_index + 1}/{total_documents} queued)")
                    document_index += 1
                except Exception as submit_error:
                    print(f"[ERROR] Failed to submit new document {next_doc_name}: {submit_error}")
                    print(f"[ERROR] Process pool may be broken. Stopping dynamic queuing.")
                    process_pool_broken = True
                    break  # Stop trying to submit new work if the process pool is broken
            elif document_index >= total_documents:
                # Calculate how many futures are still running
                remaining_futures = sum(1 for f in future_to_task if not f.done())
                print(f"[DYNAMIC] Worker {worker_id} finished. No more documents to assign. ({remaining_futures} workers still active)")

    if time_limit_reached:
        print(f"[TIMED MODE] Graceful shutdown completed. Processed {documents_processed} documents before time limit.")
    elif process_pool_broken:
        print(f"[ERROR] Processing stopped due to broken process pool. {completed_count} documents processed before failure.")
        print(f"[ERROR] {total_documents - completed_count} documents were not processed due to worker crash.")
    else:
        print(f"All queued documents completed. {completed_count} documents processed with dynamic queuing.")
    
    return {"time_limit_reached": time_limit_reached, "documents_processed": documents_processed, "process_pool_broken": process_pool_broken}