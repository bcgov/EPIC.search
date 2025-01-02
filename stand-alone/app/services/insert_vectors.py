import os
import json
import uuid
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from pypdf import PdfReader
from app.database.vector_store import VectorStore
from timescale_vector.client import uuid_from_time
import pymupdf4llm
from chunking import chunk_markdown_text
import strip_markdown
from tag_extractor import explicit_and_semantic_search_large_document
from summerizer import Summerizer
import requests

COMPLETED_LOG = "completed_files.log"
INCOMPLETE_LOG = "incomplete_files.log"

# ---------------------------------------------------------------------------
# Helpers to track which files were processed
# ---------------------------------------------------------------------------
def load_completed_files():
    """Load the list of completed files from the local log file."""
    if not os.path.exists(COMPLETED_LOG):
        return set()
    with open(COMPLETED_LOG, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_completed_files(completed_file_list):
    """Append newly completed files to the local log file."""
    with open(COMPLETED_LOG, "a") as f:
        for file_name in completed_file_list:
            f.write(file_name + "\n")

def load_incomplete_files():
    """Load the list of incomplete files from the local log file."""
    if not os.path.exists(INCOMPLETE_LOG):
        return set()
    with open(INCOMPLETE_LOG, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_incomplete_files(incomplete_file_list):
    """Append newly incomplete files to the local log file."""
    with open(INCOMPLETE_LOG, "a") as f:
        for file_name in incomplete_file_list:
            f.write(file_name + "\n")

def aggregate_tags_by_chunk(results):
    """
    Given the `results` dict with a `tags_and_chunks` list of dicts,
    aggregate all tags for each unique chunk_id into one record.
    """
    aggregated = {}
    
    for item in results["tags_and_chunks"]:
        chunk_id = item["chunk_id"]  # or 'record_id'
        
        # If we haven't seen this chunk_id yet, initialize it
        if chunk_id not in aggregated:
            aggregated[chunk_id] = {
                "chunk_id": chunk_id,
                "chunk_metadata": item["chunk_metadata"],
                "chunk_text": item["chunk_text"],
                "chunk_embedding": item["chunk_embedding"],
                "tags": []
            }
        
        # Append the current tag
        aggregated[chunk_id]["tags"].append(item["tag"])
    
    # Remove any duplicate tags
    for chunk_id in aggregated:
        aggregated[chunk_id]["tags"] = list(set(aggregated[chunk_id]["tags"]))
    
    return aggregated

# ---------------------------------------------------------------------------
# The core function that reads and processes a PDF (embedding, summarizing, etc.)
# ---------------------------------------------------------------------------
def load_data(path, base_metadata):
    """
    path: full path to the PDF file
    base_metadata: dictionary containing relevant metadata (project_id, project_name, etc.)
    """
    try:
        vec = VectorStore()
        summerizer = Summerizer()

        # 1) Convert PDF to a list of pages in Markdown
        pages = pymupdf4llm.to_markdown(path, page_chunks=True)

        # Create tables if they do not exist
        vec.create_table("document_details")
        vec.create_table("document_summary")
        vec.create_table("document_tags")

        headers = ["Header 1", "Header 2", "Header 3", "Header 4", "Header 5", "Header 6"]

        all_pages_text = []
        data_to_upsert = []

        for page_index, page_markdown in enumerate(pages):
            if not page_markdown["text"].strip():
                continue

            # page_text = strip_markdown.strip_markdown(page_markdown["text"]).strip()
            # if page_text:
                

            chunks = chunk_markdown_text(page_markdown["text"])
            if not chunks:
                print(f"No chunks found on page {page_index+1} of {path}")
                continue

            chunk_texts = []
            chunk_metadatas = []

            for chunk in chunks:
                if not hasattr(chunk, "page_content"):
                    continue

                chunk_text = strip_markdown.strip_markdown(chunk.page_content).strip()
                if not chunk_text:
                    continue
                all_pages_text.append(chunk_text)
                chunk_data = chunk.metadata if chunk.metadata else {}
                headings = [chunk_data.get(h, "") for h in headers]
                chunk_metadata = {
                    **base_metadata,
                    "page_number": str(page_index + 1),
                    "headings": headings
                }

                chunk_texts.append(chunk_text)
                chunk_metadatas.append(chunk_metadata)

            if not chunk_texts:
                continue

            embeddings = vec.get_embedding(chunk_texts)

            for i, text in enumerate(chunk_texts):
                record_id = str(uuid.uuid1())
                record = (
                    record_id,              # doc_id
                    chunk_metadatas[i],     # metadata
                    text,                   # content
                    embeddings[i],          # embedding
                )
                data_to_upsert.append(record)

        if not data_to_upsert:
            raise ValueError(f"No valid text content found for file {path}")

        # Upsert detail records into DB
        vec.upsert("document_details", data_to_upsert)

        # Keep track of chunk IDs for the summary record
        # uuid_list = [item[0] for item in data_to_upsert]

        # Summarize entire document
        # summary = summerizer.generate_summary("\n".join(all_pages_text))
        # summary_content = summary["response"]

        # Extract tags
        tags = explicit_and_semantic_search_large_document(data_to_upsert)
        all_tags = []
        all_tag_chunks = []
        tags_to_upsert = []
        unique_tags = aggregate_tags_by_chunk(tags)
        for chunk_id, chunk_info in unique_tags.items():
            if chunk_info:
                all_tags.extend(chunk_info["tags"])
                all_tag_chunks.extend(chunk_info["chunk_text"])
                tag_metadata = chunk_info["chunk_metadata"]
                tag_metadata["tags"] =  chunk_info["tags"]
                tag_record = (
                    str(uuid.uuid1()),              # doc_id
                    tag_metadata,     # metadata
                    chunk_info["chunk_text"],                   # content
                    chunk_info["chunk_embedding"],          # embedding
                )
                tags_to_upsert.append(tag_record)
        vec.upsert("document_tags", tags_to_upsert)
        # unique_tags = list(dict.fromkeys(all_tags))

        # # Summaries
        # summary_metadata = {
        #     "type": "Summary",
        #     "project_id": base_metadata["project_id"],
        #     "project_name": base_metadata["project_name"],
        #     "document_name": base_metadata["document_name"],
        #     "doc_internal_name": base_metadata["doc_internal_name"],
        #     "created_at": str(datetime.now()),
        #     "page_number": "all",
        #     "chunk_ids": json.dumps(uuid_list),
        #     "tags": ",".join(unique_tags),
        # }
        # summary_embedding = vec.get_embedding([summary_content])[0]
        # summary_record = (
        #     str(uuid.uuid1()),  # doc_id for summary
        #     summary_metadata,    # metadata
        #     summary_content,     # content
        #     summary_embedding    # embedding
        # )
        # vec.upsert("document_summary", [summary_record])

        return os.path.basename(path)

    except Exception as e:
        print(f"Exception in load_data for file {path}: {e}")
        raise

# ---------------------------------------------------------------------------
# Batch-processor that calls load_data in parallel for a list of files
# ---------------------------------------------------------------------------
def process_files(file_paths, metadata_list, batch_size=5):
    """
    file_paths: list of PDF file paths
    metadata_list: parallel list of dictionaries with metadata for each file
    batch_size: how many files to process concurrently

    NOTE: file_paths[i] corresponds to metadata_list[i].
    """
    if len(file_paths) != len(metadata_list):
        raise ValueError("file_paths and metadata_list must have the same length.")

    completed = load_completed_files()
    incomplete = load_incomplete_files()

    # Filter out files already in completed/incomplete logs
    data = [
        (path, meta)
        for (path, meta) in zip(file_paths, metadata_list)
        if (os.path.basename(path) not in completed) 
           and (os.path.basename(path) not in incomplete)
    ]

    while data:
        batch = data[:batch_size]
        data = data[batch_size:]
        if not batch:
            print("No files left to process.")
            break

        completed_this_round = []
        incomplete_this_round = []

        # We run load_data in parallel using ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=batch_size) as executor:
            future_map = {
                executor.submit(load_data, file_path, base_meta): (file_path, base_meta)
                for (file_path, base_meta) in batch
            }
            for future in as_completed(future_map):
                file_path, base_meta = future_map[future]
                file_name = os.path.basename(file_path)
                try:
                    result = future.result()
                    if result:
                        completed_this_round.append(result)
                except Exception as e:
                    print(f"Failed to process {file_name}, marking as incomplete.")
                    incomplete_this_round.append(file_name)

        # Update logs
        if completed_this_round:
            save_completed_files(completed_this_round)
            completed.update(completed_this_round)
        if incomplete_this_round:
            save_incomplete_files(incomplete_this_round)
            incomplete.update(incomplete_this_round)

    print("All possible files processed for this batch.")

# ---------------------------------------------------------------------------
# Example usage: loop over projects, call EAGLE API, gather existing PDFs, then process them
# ---------------------------------------------------------------------------
def main():
    projects = [
        # {
        #     "id": "588511eeaaecd9001b828062",
        #     "name": "Aurora LNG Digby Island"
        # },
        {
            "id": "5885119caaecd9001b822d93",
            "name": "Murray River Coal"
        },
        {
            "id": "5885117aaaecd9001b820ae9",
            "name": "Mount McDonald Wind Power"
        },
    ]

    base_url = "https://eagle-prod.apps.silver.devops.gov.bc.ca/api/public/search"

    for project in projects:
        project_id = project["id"]
        project_name = project["name"]
        print(f"\n=== Retrieving documents for project: {project_name} ({project_id}) ===")

        url = f"{base_url}?dataset=Document&project={project_id}&pageSize=25"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Error {response.status_code} fetching documents for {project_id}")
                continue

            data = response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                print(f"No data array returned for {project_id}")
                continue

            # According to the sample response, the actual docs are in the first element's "searchResults" key
            search_results = data[0].get("searchResults", [])

            file_paths = []
            metadata_list = []

            # For each doc from the API, see if we have that PDF locally
            for doc in search_results:
                doc_filename = doc.get("internalName", "").strip()
                doc_original_name =  doc.get("internalOriginalName", "").strip()
                if not doc_filename.lower().endswith(".pdf"):
                    # If it's not a PDF or empty, skip
                    continue

                local_file_path = os.path.join('app/data',project_id, doc_filename)
                if os.path.exists(local_file_path):
                    # Build doc-specific metadata based on API fields + project info
                    doc_base_metadata = {
                        "document_type": doc.get("type", "Unspecified"),
                        "project_id": project_id,
                        "project_name": project_name,
                        "document_name":doc_original_name ,
                        "doc_internal_name" :doc_filename, 
                        "created_at": str(datetime.now()),
                    }
                    file_paths.append(local_file_path)
                    metadata_list.append(doc_base_metadata)
                # else: file not found locally, skip or log as needed

            if file_paths:
                print(f"Found {len(file_paths)} local PDF(s) for {project_name}. Processing...")
                process_files(file_paths, metadata_list, batch_size=1)
            else:
                print(f"No local PDFs found to process for {project_name}.")

        except requests.exceptions.RequestException as e:
            print(f"Failed to request documents for {project_id}: {e}")

if __name__ == "__main__":
    main()
