import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from .logger import log_processing_result
from .loader import load_data

def process_files(project_id, file_keys, metadata_list, batch_size=4):
    """
    Process a batch of files by loading and embedding their contents.
    
    This function processes files in batches using a ProcessPoolExecutor for parallel execution.
    For each file, it attempts to load and process the data, then logs the result.
    
    Args:
        project_id (str): The ID of the project these files belong to
        file_keys (list): List of file keys or paths to be processed
        metadata_list (list): List of metadata dictionaries corresponding to each file
        batch_size (int, optional): Number of files to process in parallel. Defaults to 4.
        
    Raises:
        ValueError: If file_keys and metadata_list have different lengths
        
    Returns:
        None: Results are logged through the logging system
    """
    if len(file_keys) != len(metadata_list):
        raise ValueError("file_keys and metadata_list must have the same length.")

    tasks = list(zip(file_keys, metadata_list))

    if not tasks:
        print("No files to process.")
        return

    while tasks:
        batch = tasks[:batch_size]
        tasks = tasks[batch_size:]

        executor = ProcessPoolExecutor(max_workers=batch_size)
        
        try:
            futures = {
                executor.submit(load_data, file_key, base_meta): (file_key, base_meta)
                for (file_key, base_meta) in batch
            }
            for future in as_completed(futures):
                file_key, base_meta = futures[future]
                doc_id = base_meta.get("document_id") or os.path.basename(file_key)
                project_id = base_meta.get("project_id", "")

                try:
                    result = future.result()
                    print(f"Successfully processed: {result}")
                    log_processing_result(project_id, doc_id, "success")
                except Exception as e:
                    print(f"Failed to process {doc_id}: {e}")
                    log_processing_result(project_id, doc_id, "failure")
        finally:
            # Ensure executor is properly shutdown
            executor.shutdown(wait=True)

    print("All possible files processed for this batch.")
