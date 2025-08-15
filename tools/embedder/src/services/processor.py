import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from .logger import log_processing_result
from .loader import load_data
from src.utils.progress_tracker import progress_tracker

def process_files(project_id, file_keys, metadata_list, api_docs_list, batch_size=4, temp_dir=None):
    """
    Process files concurrently using a thread/process pool pattern.
    As soon as a worker is free, it picks up the next file, maximizing throughput.
    
    Args:
        project_id (str): The ID of the project these files belong to
        file_keys (list): List of file keys or paths to be processed
        metadata_list (list): List of metadata dictionaries corresponding to each file
        api_docs_list (list): List of API document objects corresponding to each file
        batch_size (int, optional): Number of files to process in parallel. Defaults to 4.
        temp_dir (str, optional): Temporary directory for processing files. Passed to load_data.
        
    Raises:
        ValueError: If file_keys, metadata_list, and api_docs_list have different lengths
        
    Returns:
        None: Results are logged through the logging system
    """
    if len(file_keys) != len(metadata_list) or len(file_keys) != len(api_docs_list):
        raise ValueError("file_keys, metadata_list, and api_docs_list must have the same length.")

    tasks = list(zip(file_keys, metadata_list, api_docs_list))

    if not tasks:
        print("No files to process.")
        return

    print(f"Starting ProcessPoolExecutor with max_workers={batch_size}")
    with ProcessPoolExecutor(max_workers=batch_size) as executor:
        future_to_task = {}
        
        # Submit all tasks
        for i, (file_key, base_meta, api_doc) in enumerate(tasks):
            worker_id = f"w{i+1}"
            doc_name = api_doc.get('displayName', api_doc.get('name', os.path.basename(file_key)))
            if len(doc_name) > 80:
                doc_name = doc_name[:77] + "..."
            
            # Extract file size and estimated page count from api_doc
            # File size is stored in 'internalSize' field as a string, convert to int
            file_size_raw = api_doc.get('internalSize', '0')
            try:
                file_size_bytes = int(file_size_raw) if file_size_raw else 0
            except (ValueError, TypeError):
                file_size_bytes = 0
            
            size_mb = file_size_bytes / (1024 * 1024) if file_size_bytes > 0 else None
            
            # Estimate page count from file size (rough estimate: ~50KB per page for PDFs)
            estimated_pages = max(1, int(file_size_bytes / 50000)) if file_size_bytes > 0 else None
            
            future = executor.submit(load_data, file_key, base_meta, temp_dir, api_doc)
            future_to_task[future] = (file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb)
            
            # Only register the first batch_size documents as active (they start immediately)
            if i < batch_size:
                progress_tracker.start_document_processing(worker_id, doc_name, estimated_pages, size_mb)
        
        completed_count = 0
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            file_key, base_meta, api_doc, worker_id, doc_name, estimated_pages, size_mb = future_to_task[future]
            doc_id = base_meta.get("document_id") or os.path.basename(file_key)
            project_id = base_meta.get("project_id", "")
            
            try:
                result = future.result()
                
                # Register completion
                if result is None:
                    print(f"File {doc_id} processing completed with None result (status already logged internally).")
                    progress_tracker.finish_document_processing(worker_id, success=False, skipped=True)
                else:
                    print(f"Successfully processed: {result}")
                    log_processing_result(project_id, doc_id, "success")
                    # For successful processing, pass the page/size info
                    progress_tracker.finish_document_processing(worker_id, success=True, pages=estimated_pages, size_mb=size_mb)
                    
            except Exception as e:
                print(f"Failed to process {doc_id}: {e}")
                log_processing_result(project_id, doc_id, "failure")
                progress_tracker.finish_document_processing(worker_id, success=False, skipped=False)
                
            completed_count += 1
            
            # When a worker finishes, start the next queued document if there is one
            next_index = completed_count + batch_size - 1  # Index of next document to start
            if next_index < len(tasks):
                # Find the future for the next document to start
                futures_list = list(future_to_task.keys())
                if next_index < len(futures_list):
                    next_future = futures_list[next_index]
                    if not next_future.done():  # Make sure it hasn't completed already
                        _, _, _, next_worker_id, next_doc_name, next_pages, next_size_mb = future_to_task[next_future]
                        progress_tracker.start_document_processing(next_worker_id, next_doc_name, next_pages, next_size_mb)

    print("All possible files processed for this project.")
