import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from .logger import log_processing_result
from .loader import load_data

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
        for file_key, base_meta, api_doc in tasks:
            future = executor.submit(load_data, file_key, base_meta, temp_dir, api_doc)
            future_to_task[future] = (file_key, base_meta, api_doc)
        for future in as_completed(future_to_task):
            file_key, base_meta, api_doc = future_to_task[future]
            doc_id = base_meta.get("document_id") or os.path.basename(file_key)
            project_id = base_meta.get("project_id", "")
            try:
                result = future.result()
                if result is None:
                    print(f"File {doc_id} was skipped or invalid. Marking as failed.")
                    log_processing_result(project_id, doc_id, "failure")
                else:
                    print(f"Successfully processed: {result}")
                    log_processing_result(project_id, doc_id, "success")
            except Exception as e:
                print(f"Failed to process {doc_id}: {e}")
                log_processing_result(project_id, doc_id, "failure")

    print("All possible files processed for this project.")
