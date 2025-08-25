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
from src.services.processor import process_project_files
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

def process_projects(project_ids=None, skip_hnsw_indexes=False, retry_failed_only=False, retry_skipped_only=False, timed_mode=False, time_limit_minutes=None, max_pages=None):
    """
    Process documents for one or more specific projects, or all projects.
    
    This function:
    1. Initializes the database connections
    2. Fetches project information from the API
    3. For each project, retrieves its documents
    4. Filters out already processed documents (or includes only failed/skipped ones in retry mode)
    5. Processes documents using continuous queue with dynamic worker allocation
    
    Args:
        project_ids (list or str, optional): Process specific project(s). Can be a single ID string or list of IDs. If None, all projects are processed.
        skip_hnsw_indexes (bool, optional): Skip creation of HNSW vector indexes for faster startup.
        retry_failed_only (bool, optional): If True, only process documents that previously failed processing.
        retry_skipped_only (bool, optional): If True, only process documents that were previously skipped.
        timed_mode (bool, optional): If True, run in timed mode with time limit.
        time_limit_minutes (int, optional): Time limit in minutes for timed mode processing.
        max_pages (int, optional): Skip documents with more than this many pages to avoid threading/memory issues.
        
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
    
    # Show max pages limit if enabled
    if max_pages is not None:
        print(f"[LIMIT] Max pages per document: {max_pages} (large documents will be skipped)")
    
    # Show processing mode
    if retry_failed_only and retry_skipped_only:
        print(f"[MODE] RETRY FAILED & SKIPPED MODE: Processing documents that previously failed OR were skipped")
    elif retry_failed_only:
        print(f"[MODE] RETRY FAILED MODE: Only processing documents that previously failed")
    elif retry_skipped_only:
        print(f"[MODE] RETRY SKIPPED MODE: Only processing documents that were previously skipped")
    else:
        print(f"[MODE] NORMAL MODE: Processing new documents (skipping successful ones)")
    
    # Initialize timing for timed mode
    start_time = datetime.now()
    time_limit_reached = False
    
    if timed_mode:
        print(f"[TIMED MODE] Running for {time_limit_minutes} minutes. Will gracefully stop after time limit.")
        print(f"[TIMED MODE] Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        time_limit_seconds = time_limit_minutes * 60
    else:
        time_limit_seconds = None
    
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

    # Note: We'll initialize progress tracking after building the document queue
    # so we have the accurate count of documents that will actually be processed
    
    results = []
    embedder_temp_dir = get_embedder_temp_dir()
    
    # Determine processing mode: dynamic queuing or sequential
    # Use dynamic queuing for all cases for maximum efficiency
    use_dynamic_processing = True  # Always use dynamic processing for maximum efficiency
    
    print(f"[DEBUG] Processing mode determination:")
    print(f"[DEBUG] - Number of projects: {len(projects)}")
    print(f"[DEBUG] - Use dynamic processing: {use_dynamic_processing}")
    
    if use_dynamic_processing:
        mode_type = "NORMAL"
        if retry_failed_only and retry_skipped_only:
            mode_type = "RETRY FAILED & SKIPPED"
        elif retry_failed_only:
            mode_type = "RETRY FAILED"
        elif retry_skipped_only:
            mode_type = "RETRY SKIPPED"
            
        print(f"\n=== DYNAMIC {mode_type} PROCESSING MODE ===")
        if len(projects) > 1:
            print(f"Processing {len(projects)} projects with unified worker pool to maximize throughput")
            print(f"All {settings.multi_processing_settings.files_concurrency_size} workers will stay busy across projects")
            print(f"CROSS-PROJECT QUEUE: Documents from different projects will be processed in continuous queue for optimal worker utilization")
        elif len(projects) > 1:
            print(f"Processing {len(projects)} projects with unified worker pool to maximize throughput")
            print(f"All {settings.multi_processing_settings.files_concurrency_size} workers will stay busy across projects")
            print(f"CROSS-PROJECT QUEUE: Documents from different projects will be processed in continuous queue for optimal worker utilization")
        else:
            print(f"Processing single project with dynamic worker queuing to maximize throughput")
            print(f"All {settings.multi_processing_settings.files_concurrency_size} workers will stay busy with continuous document queuing")
            print(f"DYNAMIC QUEUING: Workers immediately get next document when they finish current one")
        results = process_projects_in_parallel(projects, embedder_temp_dir, start_time, timed_mode, time_limit_seconds, retry_failed_only, retry_skipped_only, max_pages)
    else:
        # This branch should never be reached now since use_dynamic_processing is always True
        print(f"\n=== FALLBACK SEQUENTIAL PROCESSING ===")
        print(f"This should not happen - please report as a bug")
        return {"message": "Error: Fallback sequential processing triggered", "results": []}      

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
            print(f"TIMED MODE COMPLETED: Stopped after {total_elapsed_minutes:.1f} minutes (limit: {time_limit_minutes} minutes)")
        else:
            print(f"TIMED MODE COMPLETED: Finished all work in {total_elapsed_minutes:.1f} minutes (limit: {time_limit_minutes} minutes)")
        
        if retry_failed_only and retry_skipped_only:
            print(f"Processed failed and skipped documents for {len(results)} project(s)")
        elif retry_failed_only:
            print(f"Processed failed documents for {len(results)} project(s)")
        elif retry_skipped_only:
            print(f"Processed skipped documents for {len(results)} project(s)")
        else:
            print(f"Processed new documents for {len(results)} project(s)")
    else:
        if retry_failed_only and retry_skipped_only:
            print(f"RETRY COMPLETED: Finished retrying failed and skipped documents for {len(results)} project(s)")
        elif retry_failed_only:
            print(f"RETRY COMPLETED: Finished retrying failed documents for {len(results)} project(s)")
        elif retry_skipped_only:
            print(f"RETRY COMPLETED: Finished retrying skipped documents for {len(results)} project(s)")
        else:
            print(f"PROCESSING COMPLETED: Finished processing new documents for {len(results)} project(s)")

    # Stop progress tracking
    reason = "Completed"
    if timed_mode and time_limit_reached:
        reason = f"Time limit reached ({time_limit_minutes} minutes)"
    elif retry_failed_only and retry_skipped_only:
        reason = "Retry failed and skipped mode completed"
    elif retry_failed_only:
        reason = "Retry failed mode completed"
    elif retry_skipped_only:
        reason = "Retry skipped mode completed"
    
    progress_tracker.stop(reason)

    return {"message": "Processing completed", "results": results}


def process_projects_in_parallel(projects, embedder_temp_dir, start_time, timed_mode, time_limit_seconds, retry_failed_only=False, retry_skipped_only=False, max_pages=None):
    """Process multiple projects in parallel using a unified document queue across all projects"""
    from collections import namedtuple
    
    # Perform bulk cleanup ONLY when needed (before building document queue)
    project_ids = [project["_id"] for project in projects]
    cleanup_performed = False
    cleaned_files_to_process = []  # Track specific files that were cleaned and need processing
    
    if retry_failed_only:
        # Cleanup failed documents before retrying
        from src.services.repair_service import bulk_cleanup_failed_documents
        
        print(f"\n{'='*80}")
        print("BULK CLEANUP MODE: Cleaning up ALL failed documents before retry...")
        cleanup_result = bulk_cleanup_failed_documents(project_ids)
        cleanup_performed = True
        cleaned_files_to_process.extend(cleanup_result.get('cleaned_files', []))
        print(f"Failed documents cleaned: {cleanup_result['documents_cleaned']}")
        print(f"Failed files to reprocess: {len(cleanup_result.get('cleaned_files', []))}")
        print(f"{'='*80}")
        print("Starting targeted processing - cleaned failed documents will be queued for reprocessing")
        print(f"{'='*80}\n")
        
    if retry_skipped_only:
        # Cleanup skipped documents before retrying
        from src.services.repair_service import bulk_cleanup_skipped_documents
        
        print(f"\n{'='*80}")
        print("SKIPPED CLEANUP MODE: Cleaning up ALL skipped documents before retry...")
        cleanup_result = bulk_cleanup_skipped_documents(project_ids)
        cleanup_performed = True
        cleaned_files_to_process.extend(cleanup_result.get('cleaned_files', []))
        print(f"Skipped documents cleaned: {cleanup_result['documents_cleaned']}")
        print(f"Skipped files to reprocess: {len(cleanup_result.get('cleaned_files', []))}")
        print(f"{'='*80}")
        print("Starting targeted processing - cleaned skipped documents will be queued for reprocessing")
        print(f"{'='*80}\n")
    
    # Create a unified queue of all documents across all projects
    DocumentTask = namedtuple('DocumentTask', ['project_id', 'project_name', 's3_key', 'metadata', 'api_doc'])
    document_queue = []
    project_results = {}
    
    mode_desc = "new documents"
    if retry_failed_only and retry_skipped_only:
        mode_desc = "failed and skipped documents"
    elif retry_failed_only:
        mode_desc = "failed documents"
    elif retry_skipped_only:
        mode_desc = "skipped documents"
    
    # OPTIMIZATION: Filter projects to only those that have documents to retry/repair
    projects_to_process = projects
    if cleanup_performed and cleaned_files_to_process:
        # Extract unique project IDs from cleaned files
        cleaned_project_ids = set(f['project_id'] for f in cleaned_files_to_process)
        
        # Filter projects list to only include those with documents to retry
        projects_to_process = [p for p in projects if p["_id"] in cleaned_project_ids]
        
        print(f"\n🎯 OPTIMIZATION: Filtered to {len(projects_to_process)} projects with {mode_desc} (from {len(projects)} total projects)")
        if len(projects_to_process) < len(projects):
            projects_skipped = len(projects) - len(projects_to_process)
            print(f"   Skipping {projects_skipped} projects with no {mode_desc} - avoiding unnecessary API calls")
    
    print(f"\n=== Building unified document queue across {len(projects_to_process)} projects ({mode_desc}) ===")
    
    # Build the unified document queue
    for project in projects_to_process:
        project_id = project["_id"]
        project_name = project["name"]
        project_results[project_id] = {"project_name": project_name, "duration_seconds": 0}
        
        # Ensure project record exists
        upsert_project(project_id, project_name, project)
        
        print(f"Queuing documents from project: {project_name} ({project_id})")
        
        files_count = get_files_count_for_project(project_id)
        page_size = settings.api_pagination_settings.documents_page_size
        file_total_pages = (files_count + page_size - 1) // page_size
        
        already_completed = load_completed_files(project_id)
        already_incomplete = load_incomplete_files(project_id)
        already_skipped = load_skipped_files(project_id)
        
        documents_queued = 0
        
        # Strategy: Handle different processing modes
        # 1. If we have cleaned files from bulk cleanup, queue them first
        # 2. If retry_skipped_only is enabled, also scan for skipped files
        # 3. Otherwise, do normal discovery (new files, repair candidates, etc.)
        
        need_normal_discovery = True  # Will be set to False if we handle everything with targeted approaches
        
        # STEP 1: Handle cleaned files from bulk cleanup (failed or repair)
        if cleaned_files_to_process:
            # Filter cleaned files for this specific project
            project_cleaned_files = [f for f in cleaned_files_to_process if f['project_id'] == project_id]
            
            if project_cleaned_files:
                print(f"Found {len(project_cleaned_files)} cleaned files to reprocess for {project_name}")
                
                # For each cleaned file, find it in the API and queue it for processing
                for cleaned_file in project_cleaned_files:
                    doc_id = cleaned_file['document_id']
                    
                    # Find the document in the API to get full metadata
                    doc_found = False
                    for search_page in range(file_total_pages):
                        search_files = get_files_for_project(project_id, search_page, page_size)
                        for doc in search_files:
                            if doc["_id"] == doc_id:
                                doc_found = True
                                s3_key = doc.get("internalURL")  # Get the actual S3 key from API
                                if s3_key:
                                    doc_meta = format_metadata(project, doc)
                                    document_task = DocumentTask(
                                        project_id=project_id,
                                        project_name=project_name,
                                        s3_key=s3_key,
                                        metadata=doc_meta,
                                        api_doc=doc
                                    )
                                    document_queue.append(document_task)
                                    documents_queued += 1
                                else:
                                    print(f"Warning: Cleaned file {doc_id[:12]}... has no internalURL in API")
                                break
                        if doc_found:
                            break
                    
                    if not doc_found:
                        print(f"Warning: Cleaned file {doc_id[:12]}... not found in API (may have been deleted from S3)")
                
                print(f"Queued {len(project_cleaned_files)} cleaned documents from {project_name}")
                
                # If we're in retry-only mode (failed or skipped), we're done after cleanup
                if retry_failed_only or retry_skipped_only:
                    need_normal_discovery = False
        

        
        # If we handled everything with targeted approaches, continue to next project
        if not need_normal_discovery:
            print(f"Total queued for {project_name}: {documents_queued} documents")
            continue
        
        # Normal mode: iterate through all files
        for file_page_number in range(file_total_pages):
                files_data = get_files_for_project(project_id, file_page_number, page_size)
                
                if not files_data:
                    continue
                    
                for doc in files_data:
                    doc_id = doc["_id"]
                    doc_name = doc.get('name', doc_id)
                    is_processed, status = is_document_already_processed(
                        doc_id, already_completed, already_incomplete, already_skipped
                    )
                    
                    # Handle retry modes
                    if retry_failed_only and retry_skipped_only:
                        # Combined mode: process both failed and skipped documents
                        if not is_processed or (status != "failed" and status != "skipped"):
                            continue
                        
                        status_type = "failed" if status == "failed" else "skipped"
                        print(f"Queuing {status_type} document for retry: {doc_name}")
                        
                    elif retry_failed_only:
                        # Only process files that previously failed
                        if not is_processed or status != "failed":
                            continue
                        print(f"Queuing failed document for retry: {doc_name}")
                        
                    elif retry_skipped_only:
                        # Only process files that were previously skipped
                        if not is_processed or status != "skipped":
                            continue
                        print(f"Queuing skipped document for retry: {doc_name}")
                        
                    else:
                        # Normal mode: skip already processed files
                        if is_processed:
                            continue                
                        
                    s3_key = doc.get("internalURL")
                    if not s3_key:
                        continue
                        
                    doc_meta = format_metadata(project, doc)
                    document_task = DocumentTask(
                        project_id=project_id,
                        project_name=project_name,
                        s3_key=s3_key,
                        metadata=doc_meta,
                        api_doc=doc
                    )
                    document_queue.append(document_task)
                    documents_queued += 1
        
        print(f"Queued {documents_queued} documents from {project_name}")
    
    total_documents = len(document_queue)
    print(f"\n=== Unified queue built: {total_documents} documents across {len(projects)} projects ===")
    
    # Initialize progress tracking with accurate document count
    if timed_mode:
        print(f"TIMED MODE: {time_limit_seconds / 60:.1f} minutes limit")
    
    # Show processing mode for clarity
    if retry_failed_only and retry_skipped_only:
        print(f"RETRY MODE: Processing {total_documents} failed and skipped documents")
    elif retry_failed_only:
        print(f"RETRY MODE: Processing {total_documents} failed documents")
    elif retry_skipped_only:
        print(f"RETRY MODE: Processing {total_documents} skipped documents")
    else:
        print(f"NORMAL MODE: Processing {total_documents} new documents")
    
    # Collect document IDs for retry mode tracking
    is_retry = retry_failed_only or retry_skipped_only
    retry_doc_ids = []
    if is_retry and document_queue:
        retry_doc_ids = [task.metadata.get("document_id", f"unknown_{i}") for i, task in enumerate(document_queue)]
    
    progress_tracker.start(len(projects), total_documents, project_ids, is_retry_mode=is_retry, retry_document_ids=retry_doc_ids, timed_mode=timed_mode, time_limit_minutes=time_limit_seconds/60 if time_limit_seconds else None)
    
    if total_documents == 0:
        print(f"No {mode_desc} to process across all projects")
        return list(project_results.values())
    
    # Process documents using continuous queue - workers pull tasks dynamically
    files_concurrency_size = settings.multi_processing_settings.files_concurrency_size
    
    print(f"Processing {total_documents} documents with {files_concurrency_size} workers using continuous queue")
    print(f"Workers will continuously pull from queue - maximizing CPU utilization")
    
    # Use the unified project processor with all documents at once
    # This creates a true continuous queue where workers pull documents as they finish
    processing_result = process_project_files(
        document_queue,  # Pass all documents as one big queue
        [task.s3_key for task in document_queue],
        [task.metadata for task in document_queue],
        [task.api_doc for task in document_queue],
        batch_size=files_concurrency_size,
        temp_dir=embedder_temp_dir,
        is_retry=(retry_failed_only or retry_skipped_only),
        timed_mode=timed_mode,
        time_limit_seconds=time_limit_seconds,
        start_time=start_time,
        max_pages=max_pages,
    )
    
    # Handle timed mode results
    if timed_mode and processing_result.get("time_limit_reached"):
        print(f"\n[TIMED MODE] Processing stopped due to time limit.")
        print(f"[TIMED MODE] Documents processed: {processing_result.get('documents_processed', 0)}")
        
        # Update progress tracking with actual processed count
        for _ in range(processing_result.get('documents_processed', 0)):
            progress_tracker.increment_processed()
    
    # Calculate final results
    for project_id in project_results:
        # For cross-project mode, we don't track individual project durations accurately
        # since documents are interleaved. Set a placeholder value.
        project_results[project_id]["duration_seconds"] = 0
    
    return list(project_results.values())


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
            "--skip-hnsw-indexes", action="store_true", help="Skip creation of HNSW vector indexes for semantic search (faster startup, less resource usage)."
        )
        parser.add_argument(
            "--retry-failed", action="store_true", help="Only process documents that previously failed processing. Deletes existing processing logs and any partial data, then reprocesses from scratch."
        )
        parser.add_argument(
            "--retry-skipped", action="store_true", help="Only process documents that were previously skipped. Deletes existing processing logs and reprocesses from scratch."
        )
        parser.add_argument(
            "--timed", type=int, metavar="MINUTES", help="Run in timed mode for the specified number of minutes, then gracefully stop. Example: --timed 60"
        )
        parser.add_argument(
            "--max-pages", type=int, metavar="PAGES", help="Skip documents with more than the specified number of pages to avoid threading/memory issues with large documents. Example: --max-pages 50"
        )
        args = parser.parse_args()

        # Validate flag combinations
        # Note: --retry-failed and --retry-skipped can now be used together
        # to process both failed and skipped documents
        
        # Validate timed argument
        if args.timed is not None and args.timed <= 0:
            parser.error("Timed mode requires a positive number of minutes. Example: --timed 60")

        timed_mode = args.timed is not None
        time_limit_minutes = args.timed if timed_mode else None

        if args.project_id:
            # Run immediately if project_id(s) are provided
            result = process_projects(args.project_id, skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed, retry_skipped_only=args.retry_skipped, timed_mode=timed_mode, time_limit_minutes=time_limit_minutes, max_pages=args.max_pages)
            print(result)
        else:
            # Run for all projects if no project_id is provided
            print("No project_id provided. Processing all projects.")
            result = process_projects(skip_hnsw_indexes=args.skip_hnsw_indexes, retry_failed_only=args.retry_failed, retry_skipped_only=args.retry_skipped, timed_mode=timed_mode, time_limit_minutes=time_limit_minutes, max_pages=args.max_pages)
            print(result)
    finally:
        pass
