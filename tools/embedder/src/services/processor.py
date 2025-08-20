import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from .logger import log_processing_result
from .loader import load_data
from src.utils.progress_tracker import progress_tracker

def process_files(project_id, file_keys, metadata_list, api_docs_list, batch_size=4, temp_dir=None, is_retry=False):
    """
    Process files concurrently using continuous queue (dynamic worker allocation).
    Workers continuously pull new documents as they finish, maximizing throughput.
    
    DEPRECATED: This function is retained for compatibility but now delegates to 
    the unified continuous queue processor for optimal performance.
    
    Args:
        project_id (str): The ID of the project these files belong to
        file_keys (list): List of file keys or paths to be processed
        metadata_list (list): List of metadata dictionaries corresponding to each file
        api_docs_list (list): List of API document objects corresponding to each file
        batch_size (int, optional): Number of workers to process in parallel. Defaults to 4.
        temp_dir (str, optional): Temporary directory for processing files. Passed to load_data.
        is_retry (bool, optional): If True, cleanup existing document content before processing.
        
    Raises:
        ValueError: If file_keys, metadata_list, and api_docs_list have different lengths
        
    Returns:
        None: Results are logged through the logging system
    """
    if len(file_keys) != len(metadata_list) or len(file_keys) != len(api_docs_list):
        raise ValueError("file_keys, metadata_list, and api_docs_list must have the same length.")

    if not file_keys:
        print("No files to process.")
        return

    print(f"[DEPRECATED] process_files() now uses simplified continuous processing with {batch_size} workers")
    print(f"[INFO] For optimal performance, use process_mixed_project_files() directly instead")
    
    # Simple continuous processing implementation
    print(f"Starting ProcessPoolExecutor with max_workers={batch_size}")
    with ProcessPoolExecutor(max_workers=batch_size) as executor:
        # Submit all tasks at once - this creates a true continuous queue
        futures = []
        for i, (file_key, base_meta, api_doc) in enumerate(zip(file_keys, metadata_list, api_docs_list)):
            worker_id = i % batch_size + 1
            doc_name = api_doc.get('displayName', api_doc.get('name', os.path.basename(file_key)))
            if len(doc_name) > 80:
                doc_name = doc_name[:77] + "..."
            
            # Extract file size for progress tracking
            file_size_raw = api_doc.get('internalSize', '0')
            try:
                file_size_bytes = int(file_size_raw) if file_size_raw else 0
            except (ValueError, TypeError):
                file_size_bytes = 0
            
            size_mb = file_size_bytes / (1024 * 1024) if file_size_bytes > 0 else None
            estimated_pages = max(1, int(file_size_bytes / 50000)) if file_size_bytes > 0 else None
            
            future = executor.submit(load_data, file_key, base_meta, temp_dir, api_doc, is_retry)
            futures.append((future, file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb))
            
            # Start progress tracking for initial worker pool
            if i < batch_size:
                progress_tracker.start_document_processing(worker_id, doc_name, estimated_pages, size_mb)
        
        completed_count = 0
        
        # Process completed tasks as they finish
        for future, file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb in futures:
            doc_id = base_meta.get("document_id") or os.path.basename(file_key)
            project_id = base_meta.get("project_id", "")
            
            try:
                result = future.result()
                
                if result is None:
                    print(f"File {doc_id} processing completed with None result (status already logged internally).")
                    progress_tracker.finish_document_processing(worker_id, success=False, skipped=True)
                else:
                    print(f"Successfully processed: {result}")
                    log_processing_result(project_id, doc_id, "success")
                    progress_tracker.finish_document_processing(worker_id, success=True, pages=estimated_pages, size_mb=size_mb)
                    
            except Exception as e:
                print(f"Failed to process {doc_id}: {e}")
                log_processing_result(project_id, doc_id, "failure")
                progress_tracker.finish_document_processing(worker_id, success=False, skipped=False)
                
            completed_count += 1
    
    print(f"[DEPRECATED] Completed processing {len(file_keys)} documents using continuous queue")

    print("All possible files processed for this project.")
