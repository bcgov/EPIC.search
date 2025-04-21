import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from  .logger import (
    load_completed_files,
    load_incomplete_files,
    log_processing_result,
)
from .loader import load_data

def process_files(project_id,file_keys, metadata_list, batch_size=2):
    if len(file_keys) != len(metadata_list):
        raise ValueError("file_keys and metadata_list must have the same length.")

    already_completed = load_completed_files(project_id)
    already_incomplete = load_incomplete_files(project_id)

    tasks = []
    for key, meta in zip(file_keys, metadata_list):
        doc_id = meta.get("document_id") or os.path.basename(key)
        if doc_id in already_completed or doc_id in already_incomplete:
            print(f"Skipping already processed doc: {doc_id}")
            continue
        tasks.append((key, meta))

    if not tasks:
        print("No new files to process.")
        return

    while tasks:
        batch = tasks[:batch_size]
        tasks = tasks[batch_size:]

        with ProcessPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(load_data,file_key, base_meta): (file_key, base_meta)
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

    print("All possible files processed for this batch.")
