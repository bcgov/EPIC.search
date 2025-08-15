import argparse
import logging
from datetime import datetime
from src.services.logger import load_completed_files, load_incomplete_files, load_skipped_files
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
from src.utils.progress_tracker import progress_tracker

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

def is_document_already_processed(doc_id, completed_docs, incomplete_docs, skipped_docs):
    """
    Check if a document has been previously processed (successfully, unsuccessfully, or skipped).
    
    Args:
        doc_id: The document ID to check
        completed_docs: List of successfully processed documents
        incomplete_docs: List of unsuccessfully processed documents
        skipped_docs: List of skipped documents
        
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
    
    for skipped in skipped_docs:
        if skipped["document_id"] == doc_id:
            return True, "skipped"
            
    return False, None

def get_embedder_temp_dir():
    temp_root = tempfile.gettempdir()
    temp_guid = str(uuid.uuid4())
    temp_dir = os.path.join(temp_root, f"epic_embedder_{temp_guid}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def check_time_limit(start_time, time_limit_seconds):
    """
    Check if the time limit has been reached for timed mode.
    
    Args:
        start_time (datetime): The start time of processing
        time_limit_seconds (int): Time limit in seconds
        
    Returns:
        tuple: (time_limit_reached, elapsed_minutes, remaining_minutes)
    """
    if time_limit_seconds is None:
        return False, 0, 0
    
    elapsed_time = datetime.now() - start_time
    elapsed_seconds = elapsed_time.total_seconds()
    elapsed_minutes = elapsed_seconds / 60
    remaining_seconds = max(0, time_limit_seconds - elapsed_seconds)
    remaining_minutes = remaining_seconds / 60
    
    return elapsed_seconds >= time_limit_seconds, elapsed_minutes, remaining_minutes

def process_projects(project_ids=None, shallow_mode=False, shallow_limit=None, skip_hnsw_indexes=False, retry_failed_only=False, retry_skipped_only=False, timed_mode=False, time_limit_minutes=None):
    """
    Process documents for one or more specific projects, or all projects.
    
    This function:
    1. Initializes the database connections
    2. Fetches project information from the API
    3. For each project, retrieves its documents
    4. Filters out already processed documents (or includes only failed/skipped ones in retry mode)
    5. Processes new documents in batches
    
    Args:
        project_ids (list or str, optional): Process specific project(s). Can be a single ID string or list of IDs. If None, all projects are processed.
        shallow_mode (bool, optional): If True, only process up to shallow_limit successful documents per project.
        shallow_limit (int, optional): The maximum number of successful documents to process per project in shallow mode.
        skip_hnsw_indexes (bool, optional): Skip creation of HNSW vector indexes for faster startup.
        retry_failed_only (bool, optional): If True, only process documents that previously failed processing.
        retry_skipped_only (bool, optional): If True, only process documents that were previously skipped.
        timed_mode (bool, optional): If True, run in timed mode with time limit.
        time_limit_minutes (int, optional): Time limit in minutes for timed mode processing.
        
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
    
    # Show processing mode
    if retry_failed_only:
        print(f"[MODE] 🔄 RETRY FAILED MODE: Only processing documents that previously failed")
    elif retry_skipped_only:
        print(f"[MODE] 🔄 RETRY SKIPPED MODE: Only processing documents that were previously skipped")
    else:
        print(f"[MODE] ✅ NORMAL MODE: Processing new documents (skipping successful ones)")
    
    # Initialize timing for timed mode
    start_time = datetime.now()
    time_limit_reached = False
    
    if timed_mode:
        print(f"[TIMED MODE] ⏱️  Running for {time_limit_minutes} minutes. Will gracefully stop after time limit.")
        print(f"[TIMED MODE] Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        time_limit_seconds = time_limit_minutes * 60
    else:
        time_limit_seconds = None
    
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

    # Calculate total documents for progress tracking
    total_documents = 0
    for project in projects:
        try:
            project_id = project["_id"]
            files_count = get_files_count_for_project(project_id)
            total_documents += files_count
        except Exception as e:
            print(f"Warning: Could not get file count for project {project.get('name', 'unknown')}: {e}")
    
    # Start progress tracking
    mode_info = ""
    if timed_mode:
        mode_info = f" (TIMED: {time_limit_minutes} min)"
    elif retry_failed_only:
        mode_info = " (RETRY FAILED)"
    elif retry_skipped_only:
        mode_info = " (RETRY SKIPPED)"
    
    print(f"TIMED MODE: {time_limit_minutes} minutes limit" if timed_mode else "")
    progress_tracker.start(len(projects), total_documents)

    results = []
    embedder_temp_dir = get_embedder_temp_dir()
    for project in projects:
        # Check time limit before starting each project
        if timed_mode:
            time_limit_reached, elapsed_minutes, remaining_minutes = check_time_limit(start_time, time_limit_seconds)
            if time_limit_reached:
                print(f"\n[TIMED MODE] ⏰ Time limit of {time_limit_minutes} minutes reached after {elapsed_minutes:.1f} minutes.")
                print(f"[TIMED MODE] Gracefully stopping. Completed {len(results)} project(s).")
                break
            else:
                print(f"[TIMED MODE] ⏱️  Elapsed: {elapsed_minutes:.1f}min, Remaining: {remaining_minutes:.1f}min")
        
        project_id = project["_id"]
        project_name = project["name"]

        # Update progress tracker with current project
        progress_tracker.update_current_project(project_name)

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
        already_skipped = load_skipped_files(project_id)

        # For shallow mode, count how many have been processed successfully
        shallow_success_count = len(already_completed) if shallow_mode else 0

        for file_page_number in range(file_total_pages):
            # Check time limit before processing each page of files
            if timed_mode:
                time_limit_reached, elapsed_minutes, remaining_minutes = check_time_limit(start_time, time_limit_seconds)
                if time_limit_reached:
                    print(f"[TIMED MODE] ⏰ Time limit reached during {project_name}. Stopping file processing for this project.")
                    break
            
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
                # Check time limit before processing each document
                if timed_mode:
                    time_limit_reached, elapsed_minutes, remaining_minutes = check_time_limit(start_time, time_limit_seconds)
                    if time_limit_reached:
                        print(f"[TIMED MODE] ⏰ Time limit reached during document processing for {project_name}. Stopping at {len(s3_file_keys)} documents queued.")
                        break
                
                doc_id = doc["_id"]
                doc_name = doc.get('name', doc_id)
                is_processed, status = is_document_already_processed(
                    doc_id, already_completed, already_incomplete, already_skipped
                )
                
                # Handle retry modes
                if retry_failed_only:
                    # Only process files that previously failed
                    if not is_processed or status != "failed":
                        continue
                    print(f"Retrying failed document: {doc_name}")
                elif retry_skipped_only:
                    # Only process files that were previously skipped
                    if not is_processed or status != "skipped":
                        continue
                    print(f"Retrying skipped document: {doc_name}")
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
                elif retry_skipped_only:
                    print(
                        f"Found {len(s3_file_keys)} skipped file(s) to retry for {project_name}. Processing with {files_concurrency_size} workers..."
                    )
                else:
                    print(
                        f"Found {len(s3_file_keys)} new file(s) for {project_name}. Processing with {files_concurrency_size} workers..."
                    )
                
                # Process files in batches for timed mode, or all at once for normal mode
                if timed_mode:
                    # Process in batches using the configured concurrency size for time checks
                    batch_size = files_concurrency_size  # Use configured concurrency as batch size
                    total_files = len(s3_file_keys)
                    files_processed = 0
                    
                    for i in range(0, total_files, batch_size):
                        # Check time limit before each batch
                        time_limit_reached, elapsed_minutes, remaining_minutes = check_time_limit(start_time, time_limit_seconds)
                        if time_limit_reached:
                            print(f"[TIMED MODE] ⏰ Time limit reached. Processed {files_processed}/{total_files} files for {project_name}.")
                            break
                        
                        # Get batch of files
                        end_idx = min(i + batch_size, total_files)
                        batch_s3_keys = s3_file_keys[i:end_idx]
                        batch_metadata = metadata_list[i:end_idx]
                        batch_api_docs = api_docs_list[i:end_idx]
                        
                        print(f"[TIMED MODE] Processing batch {i//batch_size + 1}: files {i+1}-{end_idx} of {total_files} (batch size: {batch_size})")
                        
                        process_files(
                            project_id,
                            batch_s3_keys,
                            batch_metadata,
                            batch_api_docs,
                            batch_size=files_concurrency_size,
                            temp_dir=embedder_temp_dir,
                        )
                        
                        files_processed = end_idx
                        
                        # Update shallow count if in shallow mode
                        if shallow_mode:
                            shallow_success_count += len(batch_s3_keys)
                            if shallow_success_count >= shallow_limit:
                                print(f"[SHALLOW MODE] Reached {shallow_success_count} processed documents for {project_name} (limit: {shallow_limit}).")
                                break
                else:
                    # Normal mode: process all files at once for maximum efficiency
                    process_files(
                        project_id,
                        s3_file_keys,
                        metadata_list,
                        api_docs_list,
                        batch_size=files_concurrency_size,
                        temp_dir=embedder_temp_dir,
                    )
                    
                # Update shallow count for normal mode
                if not timed_mode and shallow_mode:
                    shallow_success_count += len(s3_file_keys)
                    if shallow_success_count >= shallow_limit:
                        print(f"[SHALLOW MODE] Reached {shallow_success_count} processed documents for {project_name} (limit: {shallow_limit}).")
                        break
            else:
                if retry_failed_only:
                    print(f"No failed files found to retry for {project_name}")
                elif retry_skipped_only:
                    print(f"No skipped files found to retry for {project_name}")
                else:
                    print(f"No new files to process for {project_name}")

        project_end = datetime.now()
        duration = project_end - project_start
        duration_in_s = duration.total_seconds()
        print(
            f"Project processing completed for {project_name} in {duration_in_s} seconds"
        )
        
        # Mark project as completed in progress tracker
        progress_tracker.finish_project()
        
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
    total_elapsed = datetime.now() - start_time
    total_elapsed_minutes = total_elapsed.total_seconds() / 60
    
    if timed_mode:
        if time_limit_reached:
            print(f"⏰ TIMED MODE COMPLETED: Stopped after {total_elapsed_minutes:.1f} minutes (limit: {time_limit_minutes} minutes)")
        else:
            print(f"⏰ TIMED MODE COMPLETED: Finished all work in {total_elapsed_minutes:.1f} minutes (limit: {time_limit_minutes} minutes)")
        
        if retry_failed_only:
            print(f"🔄 Processed failed documents for {len(results)} project(s)")
        elif retry_skipped_only:
            print(f"🔄 Processed skipped documents for {len(results)} project(s)")
        else:
            print(f"✅ Processed new documents for {len(results)} project(s)")
    else:
        if retry_failed_only:
            print(f"🔄 RETRY COMPLETED: Finished retrying failed documents for {len(results)} project(s)")
        elif retry_skipped_only:
            print(f"🔄 RETRY COMPLETED: Finished retrying skipped documents for {len(results)} project(s)")
        else:
            print(f"✅ PROCESSING COMPLETED: Finished processing new documents for {len(results)} project(s)")

    # Stop progress tracking
    reason = "Completed"
    if timed_mode and time_limit_reached:
        reason = f"Time limit reached ({time_limit_minutes} minutes)"
    elif retry_failed_only:
        reason = "Retry failed mode completed"
    elif retry_skipped_only:
        reason = "Retry skipped mode completed"
    
    progress_tracker.stop(reason)

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
        parser.add_argument(
            "--retry-skipped", action="store_true", help="Only process documents that were previously skipped. Useful for retrying files that were skipped due to missing OCR or unsupported formats."
        )
        parser.add_argument(
            "--timed", type=int, metavar="MINUTES", help="Run in timed mode for the specified number of minutes, then gracefully stop. Example: --timed 60"
        )
        args = parser.parse_args()

        # Custom check for missing shallow limit value
        import sys
        if any(arg in sys.argv for arg in ["--shallow", "-s"]) and args.shallow is None:
            parser.error("Argument --shallow/-s requires an integer value. Example: --shallow 5")

        # Validate flag combinations
        if args.retry_failed and args.retry_skipped:
            parser.error("Cannot use both --retry-failed and --retry-skipped at the same time. Choose one retry mode.")
        
        # Validate timed argument
        if args.timed is not None and args.timed <= 0:
            parser.error("Timed mode requires a positive number of minutes. Example: --timed 60")
        
        if args.retry_failed and args.shallow:
            print("WARNING: Using --retry-failed with --shallow mode. Shallow limit will apply to failed files being retried.")
        
        if args.retry_skipped and args.shallow:
            print("WARNING: Using --retry-skipped with --shallow mode. Shallow limit will apply to skipped files being retried.")
        
        if args.timed and args.shallow:
            print("WARNING: Using --timed with --shallow mode. Both time limit and shallow limit will apply.")

        shallow_mode = args.shallow is not None
        shallow_limit = args.shallow if shallow_mode else None
        timed_mode = args.timed is not None
        time_limit_minutes = args.timed if timed_mode else None

        if args.project_id:
            # Run immediately if project_id(s) are provided
            result = process_projects(args.project_id, shallow_mode=shallow_mode, shallow_limit=shallow_limit, skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed, retry_skipped_only=args.retry_skipped, timed_mode=timed_mode, time_limit_minutes=time_limit_minutes)
            print(result)
        else:
            # Run for all projects if no project_id is provided
            print("No project_id provided. Processing all projects.")
            result = process_projects(shallow_mode=shallow_mode, shallow_limit=shallow_limit, skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed, retry_skipped_only=args.retry_skipped, timed_mode=timed_mode, time_limit_minutes=time_limit_minutes)
            print(result)
    finally:
        pass
