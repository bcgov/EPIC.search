from datetime import datetime
from src.models import init_db
from src.models import init_vec_db
# from src.models import init_vec_index
from src.services.api_utils import (
    get_files_count_for_project,
    get_project_by_id,
    get_projects,
    get_files_for_project,
    get_projects_count,
)
from src.services.processor import process_files
from src.services.data_formatter import format_metadata
import argparse


def main(project_id=None):
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
        print("No projects returned by API.")
        return

    for project in projects:
        project_id = project["_id"]
        project_name = project["name"]

        print(
            f"\n=== Retrieving documents for project: {project_name} ({project_id}) ==="
        )

        project_start = datetime.now()

        files_count = get_files_count_for_project(
            project_id
        )  # Assuming this function exists
        page_size = 50
        file_total_pages = (
            files_count + page_size - 1
        ) // page_size  # Calculate total pages for files

        for file_page_number in range(file_total_pages):
            files_data = get_files_for_project(project_id, file_page_number, page_size)
            if not files_data:
                print(f"No files found for project {project_id}")
                continue

            s3_file_keys = []
            metadata_list = []

            for doc in files_data:
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
                process_files(project_id, s3_file_keys, metadata_list, batch_size=4)

        project_end = datetime.now()
        duration = project_end - project_start
        duration_in_s = duration.total_seconds()
        print (f"Project processing completed for { project_name} in {duration_in_s} seconds")

    # Create the index at end of run - see which one makes sense for performance
    # init_vec_index()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process projects and their documents."
    )
    parser.add_argument(
        "--project_id", type=str, help="The ID of the project to process"
    )
    args = parser.parse_args()

    main(args.project_id)

