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

def process_projects(project_id=None, shallow_mode=False, shallow_limit=None):
    """
    Process documents for one or all projects.
    
    This function:
    1. Initializes the database connections
    2. Fetches project information from the API
    3. For each project, retrieves its documents
    4. Filters out already processed documents
    5. Processes new documents in batches
    
    Args:
        project_id (str, optional): Process a specific project. If None, all projects are processed.
        shallow_mode (bool, optional): If True, only process up to shallow_limit successful documents per project.
        shallow_limit (int, optional): The maximum number of successful documents to process per project in shallow mode.
        
    Returns:
        dict: A dictionary containing the processing results, including:
            - message: A status message
            - results: A list of project processing results, each with:
                - project_name: Name of the processed project
                - duration_seconds: Time taken to process the project
    """
    
    init_vec_db()

    if project_id:
        # Process a single project
        projects = []
        projects.extend(get_project_by_id(project_id))
    else:
        # Fetch and process all projects
        projects_count = get_projects_count()
        page_size = 25
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
        page_size = 50
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

            for doc in files_data:
                doc_id = doc["_id"]
                doc_name = doc.get('name', doc_id)
                is_processed, status = is_document_already_processed(
                    doc_id, already_completed, already_incomplete
                )
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
                if shallow_mode and (shallow_success_count + len(s3_file_keys)) >= shallow_limit:
                    # Only add up to the shallow limit
                    break

            if s3_file_keys:
                print(
                    f"Found {len(s3_file_keys)} file(s) for {project_name}. Processing..."
                )
                files_concurrency_size = int(
                    settings.multi_processing_settings.files_concurrency_size
                )
                process_files(
                    project_id,
                    s3_file_keys,
                    metadata_list,
                    batch_size=files_concurrency_size,
                    temp_dir=embedder_temp_dir,  # Pass temp dir to process_files
                )
                if shallow_mode:
                    shallow_success_count += len(s3_file_keys)
                    if shallow_success_count >= shallow_limit:
                        print(f"[SHALLOW MODE] Reached {shallow_success_count} processed documents for {project_name} (limit: {shallow_limit}).")
                        break

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

    return {"message": "Processing completed", "results": results}

if __name__ == "__main__":   
    # Suppress the process pool error messages that occur during shutdown
    suppress_process_pool_errors()
    
    try:
        parser = argparse.ArgumentParser(
            description="Process projects and their documents."
        )
        parser.add_argument(
            "--project_id", type=str, help="The ID of the project to process"
        )
        parser.add_argument(
            "--shallow", "-s", type=int, metavar="LIMIT", help="Enable shallow mode: process up to LIMIT successful documents per project and then move to the next project. Example: --shallow 5"
        )
        args = parser.parse_args()

        # Custom check for missing shallow limit value
        import sys
        if any(arg in sys.argv for arg in ["--shallow", "-s"]) and args.shallow is None:
            parser.error("Argument --shallow/-s requires an integer value. Example: --shallow 5")

        shallow_mode = args.shallow is not None
        shallow_limit = args.shallow if shallow_mode else None

        if args.project_id:
            # Run immediately if a project_id is provided
            result = process_projects(args.project_id, shallow_mode=shallow_mode, shallow_limit=shallow_limit)
            print(result)
        else:
            # Run for all projects if no project_id is provided
            print("No project_id provided. Processing all projects.")
            result = process_projects(shallow_mode=shallow_mode, shallow_limit=shallow_limit)
            print(result)
    finally:
        pass
