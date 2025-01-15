from datetime import datetime
from src.models import init_db
from src.models import init_vec_db
from src.services.api_utils import get_projects, get_files_for_project
from src.services.processor import process_files
from src.services.data_formatter import format_metadata
def main():

    init_db()
    init_vec_db()

    projects = get_projects()
    if not projects:
        print("No projects returned by API.")
        return

    for project in projects:
        project_id = project["_id"]
        project_name = project["name"]
        print(f"\n=== Retrieving documents for project: {project_name} ({project_id}) ===")

        files_data = get_files_for_project(project_id)
        if not files_data:
            print(f"No files found for project {project_id}")
            continue

        s3_file_keys = []
        metadata_list = []

        for doc in files_data:
      
            s3_key = doc.get("internalURL")
            if not s3_key:
                continue 

            doc_meta = format_metadata(project,doc)

            s3_file_keys.append(s3_key)
            metadata_list.append(doc_meta)

        if s3_file_keys:
            print(f"Found {len(s3_file_keys)} file(s) for {project_name}. Processing...")
            process_files(project_id,s3_file_keys, metadata_list, batch_size=1)
        else:
            print(f"No valid S3 files found for {project_name}.")

if __name__ == "__main__":
    main()
