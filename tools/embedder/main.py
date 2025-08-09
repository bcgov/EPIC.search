import argparse
import logging
from datetime import datetime
from src.services.logger import load_completed_files, load_incomplete_files
from src.models.pgvector.vector_db_utils import init_vec_db
from src.config.settings import get_settings
from src.utils.error_suppression import suppress_process_pool_errors
import tempfile
import uuid
import shutil
import os

"""
EPIC.search Embedder - Main Entry Point

This module serves as the main entry point for the EPIC.search Embedder application,
which processes PDF documents from projects and converts them into vector embeddings
for semantic search capabilities.

The application can process a single project (when a project_id is provided) or
all available projects. It tracks processing status to avoid re-processing documents
and handles parallel processing for efficiency.
"""

from src.services.api_utils import (
    get_files_count_for_project,
    get_project_by_id,
    get_projects,
    get_files_for_project,
    get_projects_count,
)
from src.services.processor import process_files
from src.services.data_formatter import format_metadata
from src.services.project_utils import upsert_project
from src.services.ocr.ocr_factory import initialize_ocr

# Initialize settings at module level
settings = get_settings()

def setup_logging():
    """
    Configure the logging system for the application.
    
    Sets up basic logging configuration with INFO level and a standard format.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

def is_document_already_processed(doc_id, completed_docs, incomplete_docs):
    """
    Check if a document has been previously processed (successfully or unsuccessfully).
    
    Args:
        doc_id: The document ID to check
        completed_docs: List of successfully processed documents
        incomplete_docs: List of unsuccessfully processed documents
        
    Returns:
        tuple: (is_processed, status_message) where is_processed is a boolean and 
               status_message is a string or None if not processed
    """
    for completed in completed_docs:
        if completed["document_id"] == doc_id:
            return True, "success"
            
    for incomplete in incomplete_docs:
        if incomplete["document_id"] == doc_id:
            return True, "failed"
            
    return False, None

def get_embedder_temp_dir():
    temp_root = tempfile.gettempdir()
    temp_guid = str(uuid.uuid4())
    temp_dir = os.path.join(temp_root, f"epic_embedder_{temp_guid}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def process_projects(project_ids=None, shallow_mode=False, shallow_limit=None, skip_hnsw_indexes=False, retry_failed_only=False):
    """
    Process documents for one or more specific projects, or all projects.
    
    This function:
    1. Initializes the database connections
    2. Fetches project information from the API
    3. For each project, retrieves its documents
    4. Filters out already processed documents (or includes only failed ones in retry mode)
    5. Processes new documents in batches
    
    Args:
        project_ids (list or str, optional): Process specific project(s). Can be a single ID string or list of IDs. If None, all projects are processed.
        shallow_mode (bool, optional): If True, only process up to shallow_limit successful documents per project.
        shallow_limit (int, optional): The maximum number of successful documents to process per project in shallow mode.
        skip_hnsw_indexes (bool, optional): Skip creation of HNSW vector indexes for faster startup.
        retry_failed_only (bool, optional): If True, only process documents that previously failed processing.
        
    Returns:
        dict: A dictionary containing the processing results, including:
            - message: A status message
            - results: A list of project processing results, each with:
                - project_name: Name of the processed project
                - duration_seconds: Time taken to process the project
    """
    
    # Print performance configuration
    files_concurrency = settings.multi_processing_settings.files_concurrency_size
    keyword_workers = settings.multi_processing_settings.keyword_extraction_workers
    chunk_batch_size = settings.multi_processing_settings.chunk_insert_batch_size
    
    print(f"[PERF] Document workers: {files_concurrency}")
    print(f"[PERF] Keyword threads per document: {keyword_workers}")
    print(f"[PERF] Database batch size: {chunk_batch_size}")
    print(f"[PERF] Total potential keyword threads: {files_concurrency * keyword_workers}")
    print(f"[PERF] Database connection pool: {32} base + {64} overflow = {96} max connections")
    
    # Show processing mode
    if retry_failed_only:
        print(f"[MODE] 🔄 RETRY FAILED MODE: Only processing documents that previously failed")
    else:
        print(f"[MODE] ✅ NORMAL MODE: Processing new documents (skipping successful ones)")
    
    # HC44-32rs specific performance info
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    if cpu_count >= 32:
        print(f"[HC44-32rs] Detected {cpu_count} vCPUs - high-performance server mode enabled")
        print(f"[HC44-32rs] Theoretical max throughput: {files_concurrency * keyword_workers} concurrent operations")
    else:
        print(f"[PERF] Detected {cpu_count} vCPUs - standard mode")
    
    # Pass skip_hnsw_indexes from main
    init_vec_db(skip_hnsw=skip_hnsw_indexes)

    if project_ids:
        # Process specific project(s)
        # Handle both single string and list of strings
        if isinstance(project_ids, str):
            project_ids = [project_ids]
        
        projects = []
        for project_id in project_ids:
            project_data = get_project_by_id(project_id)
            if project_data:
                projects.extend(project_data)
            else:
                print(f"Warning: Project ID '{project_id}' not found")
    else:
        # Fetch and process all projects
        projects_count = get_projects_count()
        page_size = settings.api_pagination_settings.project_page_size
        total_pages = (
            projects_count + page_size - 1
        ) // page_size  # Calculate total pages

        projects = []
        for page_number in range(total_pages):
            projects.extend(get_projects(page_number, page_size))

    if not projects:
        return {"message": "No projects returned by API."}

    results = []
    embedder_temp_dir = get_embedder_temp_dir()
    for project in projects:
        project_id = project["_id"]
        project_name = project["name"]

        # Ensure project record exists before processing documents
        upsert_project(project_id, project_name, project)

        print(
            f"\n=== Retrieving documents for project: {project_name} ({project_id}) ==="
        )

        if shallow_mode:
            print(f"[SHALLOW MODE] Will process up to {shallow_limit} successful documents for this project.")

        project_start = datetime.now()

        files_count = get_files_count_for_project(project_id)
        page_size = settings.api_pagination_settings.documents_page_size
        file_total_pages = (
            files_count + page_size - 1
        ) // page_size  # Calculate total pages for files

        already_completed = load_completed_files(project_id)
        already_incomplete = load_incomplete_files(project_id)

        # For shallow mode, count how many have been processed successfully
        shallow_success_count = len(already_completed) if shallow_mode else 0

        for file_page_number in range(file_total_pages):
            if shallow_mode and shallow_success_count >= shallow_limit:
                print(f"[SHALLOW MODE] {shallow_success_count} documents already processed for {project_name}, skipping rest.")
                break
            files_data = get_files_for_project(project_id, file_page_number, page_size)

            if not files_data:
                print(f"No files found for project {project_id}")
                continue

            s3_file_keys = []
            metadata_list = []
            docs_to_process = []
            api_docs_list = []  # Store API document objects

            for doc in files_data:
                doc_id = doc["_id"]
                doc_name = doc.get('name', doc_id)
                is_processed, status = is_document_already_processed(
                    doc_id, already_completed, already_incomplete
                )
                
                # Handle retry_failed_only mode
                if retry_failed_only:
                    # Only process files that previously failed
                    if not is_processed or status != "failed":
                        continue
                    print(f"Retrying failed document: {doc_name}")
                else:
                    # Normal mode: skip already processed files
                    if is_processed:
                        print(f"Skipping already processed ({status}) document: {doc_name}")
                        continue
                        
                s3_key = doc.get("internalURL")
                if not s3_key:
                    continue
                doc_meta = format_metadata(project, doc)
                s3_file_keys.append(s3_key)
                metadata_list.append(doc_meta)
                docs_to_process.append(doc)
                api_docs_list.append(doc)  # Store the API document object
                if shallow_mode and (shallow_success_count + len(s3_file_keys)) >= shallow_limit:
                    # Only add up to the shallow limit
                    break

            if s3_file_keys:
                files_concurrency_size = settings.multi_processing_settings.files_concurrency_size
                if retry_failed_only:
                    print(
                        f"Found {len(s3_file_keys)} failed file(s) to retry for {project_name}. Processing with {files_concurrency_size} workers..."
                    )
                else:
                    print(
                        f"Found {len(s3_file_keys)} new file(s) for {project_name}. Processing with {files_concurrency_size} workers..."
                    )
                process_files(
                    project_id,
                    s3_file_keys,
                    metadata_list,
                    api_docs_list,  # Pass API document objects
                    batch_size=files_concurrency_size,
                    temp_dir=embedder_temp_dir,  # Pass temp dir to process_files
                )
                if shallow_mode:
                    shallow_success_count += len(s3_file_keys)
                    if shallow_success_count >= shallow_limit:
                        print(f"[SHALLOW MODE] Reached {shallow_success_count} processed documents for {project_name} (limit: {shallow_limit}).")
                        break
            else:
                if retry_failed_only:
                    print(f"No failed files found to retry for {project_name}")
                else:
                    print(f"No new files to process for {project_name}")

        project_end = datetime.now()
        duration = project_end - project_start
        duration_in_s = duration.total_seconds()
        print(
            f"Project processing completed for {project_name} in {duration_in_s} seconds"
        )
        results.append(
            {"project_name": project_name, "duration_seconds": duration_in_s}
        )

    # After all processing, clean up the temp folder
    print(f"Cleaning up embedder temp directory: {embedder_temp_dir}")
    try:
        shutil.rmtree(embedder_temp_dir)
        print("Temp directory cleaned up.")
    except Exception as cleanup_err:
        print(f"[WARN] Could not delete temp directory {embedder_temp_dir}: {cleanup_err}")

    # Summary message
    if retry_failed_only:
        print(f"🔄 RETRY COMPLETED: Finished retrying failed documents for {len(results)} project(s)")
    else:
        print(f"✅ PROCESSING COMPLETED: Finished processing new documents for {len(results)} project(s)")

    return {"message": "Processing completed", "results": results}

if __name__ == "__main__":   
    # Suppress the process pool error messages that occur during shutdown
    suppress_process_pool_errors()
    
    # Initialize OCR processor
    initialize_ocr()
    
    try:
        parser = argparse.ArgumentParser(
            description="Process projects and their documents."
        )
        parser.add_argument(
            "--project_id", type=str, nargs='+', help="The ID(s) of the project(s) to process. Can specify multiple: --project_id id1 id2 id3"
        )
        parser.add_argument(
            "--shallow", "-s", type=int, metavar="LIMIT", help="Enable shallow mode: process up to LIMIT successful documents per project and then move to the next project. Example: --shallow 5"
        )
        parser.add_argument(
            "--skip-hnsw-indexes", action="store_true", help="Skip creation of HNSW vector indexes for semantic search (faster startup, less resource usage)."
        )
        parser.add_argument(
            "--retry-failed", action="store_true", help="Only process documents that previously failed processing. Useful for retrying files that had errors."
        )
        args = parser.parse_args()

        # Custom check for missing shallow limit value
        import sys
        if any(arg in sys.argv for arg in ["--shallow", "-s"]) and args.shallow is None:
            parser.error("Argument --shallow/-s requires an integer value. Example: --shallow 5")

        # Validate flag combinations
        if args.retry_failed and args.shallow:
            print("WARNING: Using --retry-failed with --shallow mode. Shallow limit will apply to failed files being retried.")

        shallow_mode = args.shallow is not None
        shallow_limit = args.shallow if shallow_mode else None

        if args.project_id:
            # Run immediately if project_id(s) are provided
            result = process_projects(args.project_id, shallow_mode=shallow_mode, shallow_limit=shallow_limit, skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed)
            print(result)
        else:
            # Run for all projects if no project_id is provided
            print("No project_id provided. Processing all projects.")
            result = process_projects(shallow_mode=shallow_mode, shallow_limit=shallow_limit, skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed)
            print(result)
    finally:
        pass
