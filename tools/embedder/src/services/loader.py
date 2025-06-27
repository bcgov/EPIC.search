import os
import uuid
import tempfile
import traceback
import strip_markdown

from .s3_reader import read_file_from_s3
from src.models import PgVectorStore as VectorStore
from .markdown_splitter import chunk_markdown_text
from .tag_extractor import explicit_and_semantic_search_large_document
from .data_formatter import aggregate_tags_by_chunk
from .embedding import get_embedding
from .pdf_validation import validate_pdf_file
from .markdown_reader import read_as_pages

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

def chunk_and_embed_pages(pages, base_metadata, s3_key):
    """Chunk markdown pages and generate embeddings."""
    headers = ["Header 1", "Header 2", "Header 3", "Header 4", "Header 5", "Header 6"]
    all_pages_text = []
    data_to_upsert = []
    for page_index, page_markdown in enumerate(pages):
        if not page_markdown["text"].strip():
            continue
        chunks = chunk_markdown_text(page_markdown["text"])
        if not chunks:
            print(f"No chunks found on page {page_index+1} of {s3_key}")
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
                "headings": headings,
                "s3_key": s3_key
            }
            chunk_texts.append(chunk_text)
            chunk_metadatas.append(chunk_metadata)
        if chunk_texts:
            embeddings = get_embedding(chunk_texts)
            for i, text in enumerate(chunk_texts):
                record_id = str(uuid.uuid1())
                record = {
                    "id": record_id,
                    "metadata": chunk_metadatas[i],
                    "content": text,
                    "embedding": embeddings[i],
                }
                data_to_upsert.append(record)
    return data_to_upsert

def extract_and_aggregate_tags(data_to_upsert):
    """Extract and aggregate tags from embedded chunks."""
    tags = explicit_and_semantic_search_large_document(data_to_upsert)
    unique_tags = aggregate_tags_by_chunk(tags)
    tags_to_upsert = []
    for chunk_id, chunk_info in unique_tags.items():
        if chunk_info:
            tag_metadata = chunk_info["chunk_metadata"]
            tag_metadata["tags"] = chunk_info["tags"]
            tag_record = {
                "id": str(uuid.uuid1()),
                "metadata": tag_metadata,
                "content": chunk_info["chunk_text"],
                "embedding": chunk_info["chunk_embedding"],
            }
            tags_to_upsert.append(tag_record)
    return tags_to_upsert

def load_data(s3_key, base_metadata, temp_dir=None):
    """
    Load and process a document from S3, embedding its content into the vector store.
    
    This function:
    1. Downloads the document from S3
    2. Converts PDF to markdown
    3. Splits markdown into chunks
    4. Creates embeddings for each chunk
    5. Stores chunks and embeddings in the vector store
    6. Extracts and stores tags from the document
    
    Args:
        s3_key (str): The S3 key of the file to process
        base_metadata (dict): Base metadata to attach to all chunks
        temp_dir (str, optional): Directory to use for temporary files. Defaults to system temp directory.
    
    Returns:
        str: The S3 key of the processed file if successful
        
    Raises:
        ValueError: If no valid text content is found in the file
        Exception: Any exception that occurs during processing is re-raised
    """
    doc_id = base_metadata.get("document_id") or os.path.basename(s3_key)
    project_id = base_metadata.get("project_id", "")
    print(f"[Worker] Actually processing: doc_id={doc_id}, file_key={s3_key}, project_id={project_id}")
    temp_path = None
    try:
        pdf_bytes = read_file_from_s3(s3_key)

        # Use provided temp_dir for temp file creation
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=temp_dir) as temp:
            temp.write(pdf_bytes)
            temp.flush()
            temp_path = temp.name

        # Use the new validator function
        is_valid, reason = validate_pdf_file(temp_path, s3_key)
        if not is_valid:
            if reason == "scanned_or_image_pdf":
                print(f"[SKIP] File {s3_key} is likely a scanned/image-based PDF (PDF 1.4, no extractable text). Marking as failed and deleting temp file.")
            else:
                print(f"[SKIP] File {s3_key} failed PDF validation: {reason}. Deleting temp file.")
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
            return None

        # Now, always call pymupdf4llm.to_markdown for files that pass the pre-check
        pages = read_as_pages(temp_path)

        # Abort early if all pages are empty or whitespace
        if not any(page.get("text", "").strip() for page in pages):
            print(f"[WARN] No readable text found in any page of file {s3_key}. Skipping file.")
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
            return None

        vec = VectorStore()

        data_to_upsert = chunk_and_embed_pages(pages, base_metadata, s3_key)
        if not data_to_upsert:
            print(f"[WARN] No valid text content found in file {s3_key}. Skipping file.")
            return None

        vec.insert(settings.vector_store_settings.doc_chunks_name, data_to_upsert)

        tags_to_upsert = extract_and_aggregate_tags(data_to_upsert)
        vec.insert(settings.vector_store_settings.doc_tags_name, tags_to_upsert)

        return s3_key

    except Exception as e:
        traceback_str = traceback.format_exc()
        print(f"\n[ERROR] Exception processing file:\n  S3 Key: {s3_key}\n  Doc ID: {doc_id}\n  Project ID: {project_id}\n  Error: {e}\nTraceback:\n{traceback_str}\n")
        raise
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
