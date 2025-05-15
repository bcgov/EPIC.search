import argparse
import logging
from datetime import datetime
from src.services.logger import load_completed_files, load_incomplete_files
from src.models import init_db
from src.models.pgvector.vector_db_utils import init_vec_db
from src.config.settings import get_settings
from src.utils.error_suppression import suppress_process_pool_errors

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

def process_projects(project_id=None):
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
        
    Returns:
        dict: A dictionary containing the processing results, including:
            - message: A status message
            - results: A list of project processing results, each with:
                - project_name: Name of the processed project
                - duration_seconds: Time taken to process the project
    """
    init_db()
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
    for project in projects:
        project_id = project["_id"]
        project_name = project["name"]

        print(
            f"\n=== Retrieving documents for project: {project_name} ({project_id}) ==="
        )

        project_start = datetime.now()

        files_count = get_files_count_for_project(project_id)
        page_size = 50
        file_total_pages = (
            files_count + page_size - 1
        ) // page_size  # Calculate total pages for files

        already_completed = load_completed_files(project_id)
        already_incomplete = load_incomplete_files(project_id)

        for file_page_number in range(file_total_pages):
            files_data = get_files_for_project(project_id, file_page_number, page_size)

            if not files_data:
                print(f"No files found for project {project_id}")
                continue

            s3_file_keys = []
            metadata_list = []

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

            if s3_file_keys:
                print(
                    f"Found {len(s3_file_keys)} file(s) for {project_name}. Processing..."
                )
                # Get files concurrency size from settings and cast to int
                files_concurrency_size = int(
                    settings.multi_processing_settings.files_concurrency_size
                )
                process_files(
                    project_id,
                    s3_file_keys,
                    metadata_list,
                    batch_size=files_concurrency_size,
                )

        project_end = datetime.now()
        duration = project_end - project_start
        duration_in_s = duration.total_seconds()
        print(
            f"Project processing completed for {project_name} in {duration_in_s} seconds"
        )
        results.append(
            {"project_name": project_name, "duration_seconds": duration_in_s}
        )

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
        args = parser.parse_args()

        if args.project_id:
            # Run immediately if a project_id is provided
            result = process_projects(args.project_id)
            print(result)
        else:
            # Run for all projects if no project_id is provided
            print("No project_id provided. Processing all projects.")
            result = process_projects()
            print(result)
    finally:
        pass
