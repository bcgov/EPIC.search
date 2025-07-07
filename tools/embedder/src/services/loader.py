"""
Loader module for document processing, chunking, embedding, and database upsert.

This module orchestrates the full document processing pipeline:
- Downloads and validates files
- Splits documents into pages and chunks
- Extracts tags and keywords (batched and parallelized)
- Generates chunk and document-level embeddings
- Stores all data using SQLAlchemy ORM and pgvector
- Collects and stores structured processing metrics

All database operations use SQLAlchemy ORM. Vector columns use pgvector and HNSW indexes for fast semantic search.
"""

import os
import uuid
import tempfile
import traceback
import strip_markdown
import time
import numpy as np

from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import sessionmaker
from src.models.pgvector.vector_models import DocumentChunk, Document, ProcessingLog

from .s3_reader import read_file_from_s3
from .markdown_splitter import chunk_markdown_text
from .tag_extractor import extract_tags_from_chunks
from .embedding import get_embedding
from .pdf_validation import validate_pdf_file
from .markdown_reader import read_as_pages
from .bert_keyword_extractor import extract_keywords_from_chunks

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

def build_document_embedding(tags, keywords, headings, embedding_fn):
    """
    Build a semantic embedding for a document from tags, keywords, and headings.

    Args:
        tags (list of str): Document tags.
        keywords (list of str): Document keywords.
        headings (list of str): Document headings.
        embedding_fn (callable): Function to generate embedding, e.g. get_embedding.

    Returns:
        embedding (list/np.ndarray): The embedding vector for the document.
        combined_text (str): The text used to generate the embedding.
    """
    tags_sorted = sorted(tags)
    keywords_sorted = sorted(keywords)
    headings_sorted = sorted(headings)
    combined_text = (
        " ".join(tags_sorted) + " [SEP] " +
        " ".join(keywords_sorted) + " [SEP] " +
        " ".join(headings_sorted)
    )
    embedding = embedding_fn([combined_text])[0] if combined_text.strip() else None
    return embedding, combined_text

def chunk_and_embed_pages(
    pages: List[Dict[str, Any]],
    base_metadata: Dict[str, Any],
    s3_key: str,
    metrics: dict = None
) -> Tuple[List[Dict[str, Any]], List[str], List[str], List[str], Any]:
    """
    Chunk markdown pages and generate embeddings, tags, and keywords for each chunk.
    Also aggregates all unique tags, keywords, and headings for the document.
    Optionally collects per-chunk metrics if a metrics dict is provided.

    Args:
        pages: List of page dicts with 'text' key.
        base_metadata: Metadata to attach to each chunk.
        s3_key: S3 key for the document.
        metrics: Optional dictionary to collect per-chunk metrics.

    Returns:
        chunks_to_upsert: List of chunk dicts for DB upsert.
        all_tags: Unique tags for the document.
        all_keywords: Unique keywords for the document.
        all_headings: Unique headings for the document.
    """
    headers = [f"Header {i}" for i in range(1, 7)]
    chunks_to_upsert = []
    all_tags = set()
    all_keywords = set()
    all_headings = set()
    chunk_metrics = None
    if metrics is not None:
        chunk_metrics = metrics.setdefault("chunk_and_embed_pages", {})
        chunk_metrics["pages"] = len(pages)
        chunk_metrics["chunks_per_page"] = []
        chunk_metrics["_get_tags_times"] = []
        chunk_metrics["_get_keywords_times"] = []
        chunk_metrics["_embedding_times"] = []
    for page_index, page_markdown in enumerate(pages):
        if not page_markdown.get("text", "").strip():
            if chunk_metrics is not None:
                chunk_metrics["chunks_per_page"].append(0)
            continue
        chunks = chunk_markdown_text(page_markdown["text"])
        if not chunks:
            print(f"No chunks found on page {page_index+1} of {s3_key}")
            if chunk_metrics is not None:
                chunk_metrics["chunks_per_page"].append(0)
            continue
        chunk_texts = []
        chunk_metadatas = []
        chunk_dicts = []
        page_chunk_count = 0
        for chunk in chunks:
            if not hasattr(chunk, "page_content"):
                continue
            chunk_text = strip_markdown.strip_markdown(chunk.page_content).strip()
            if not chunk_text:
                continue
            chunk_data = chunk.metadata if chunk.metadata else {}
            headings = [chunk_data.get(h, "") for h in headers]
            all_headings.update([h for h in headings if h])
            chunk_metadata = {
                **base_metadata,
                "page_number": str(page_index + 1),
                "headings": headings,
                "s3_key": s3_key,
                # tags/keywords will be filled after extraction
            }
            chunk_texts.append(chunk_text)
            chunk_metadatas.append(chunk_metadata)
            chunk_dicts.append({
                "content": chunk_text,
                "metadata": chunk_metadata,
                "id": str(uuid.uuid1()),
                # embedding will be filled later
            })
            page_chunk_count += 1
        if chunk_metrics is not None:
            chunk_metrics["chunks_per_page"].append(page_chunk_count)
        if chunk_texts:
            # Parallel tag extraction for all chunks on this page
            t_tag = time.perf_counter() if chunk_metrics is not None else None
            tag_results = extract_tags_from_chunks(chunk_dicts)
            if chunk_metrics is not None:
                chunk_metrics["_get_tags_times"].append(time.perf_counter() - t_tag)
            # Use new tag_results structure
            if tag_results and isinstance(tag_results, dict):
                # Aggregate all unique tags for the document
                all_tags.update(tag_results.get("all_matches", []))
                # Set per-chunk tags
                chunk_id_to_tags = {chunk["chunk_id"]: chunk["all_matches"] for chunk in tag_results.get("chunks", [])}
                for i, chunk_dict in enumerate(chunk_dicts):
                    chunk_id = chunk_dict["id"]
                    tags = chunk_id_to_tags.get(chunk_id, [])
                    chunk_metadatas[i]["tags"] = tags
            # Batch keyword extraction for all chunks on this page (now refactored)
            t_kw = time.perf_counter() if chunk_metrics is not None else None
            chunk_dicts, page_keywords = extract_keywords_from_chunks(chunk_dicts)
            if chunk_metrics is not None:
                chunk_metrics["_get_keywords_times"].append(time.perf_counter() - t_kw)
            all_keywords.update(page_keywords)
            for i, chunk_dict in enumerate(chunk_dicts):
                # keywords already set in chunk_metadatas[i]["keywords"] by extract_keywords_from_chunks
                pass
        if chunk_metrics is not None:
            t_emb = time.perf_counter() if chunk_metrics is not None else None
            embeddings = get_embedding(chunk_texts)
            if chunk_metrics is not None:
                chunk_metrics["_embedding_times"].append(time.perf_counter() - t_emb)
            for i, text in enumerate(chunk_texts):
                record_id = str(uuid.uuid1())
                record = {
                    "id": record_id,
                    "metadata": chunk_metadatas[i],
                    "content": text,
                    "embedding": embeddings[i],
                }
                chunks_to_upsert.append(record)
    # At the end, sum the times and store as total values
    if chunk_metrics is not None:
        chunk_metrics["get_tags_time_total"] = sum(chunk_metrics.pop("_get_tags_times", []))
        chunk_metrics["get_keywords_time_total"] = sum(chunk_metrics.pop("_get_keywords_times", []))
        chunk_metrics["embedding_time_total"] = sum(chunk_metrics.pop("_embedding_times", []))
        # Calculate average chunks per page and store as avg_chunks_per_page
        chunks_per_page = chunk_metrics.pop("chunks_per_page", [])
        if chunks_per_page:
            chunk_metrics["avg_chunks_per_page"] = sum(chunks_per_page) / len(chunks_per_page)
        else:
            chunk_metrics["avg_chunks_per_page"] = 0.0
    # After all_tags, all_keywords, all_headings are finalized, build semantic embedding
    semantic_embedding, _ = build_document_embedding(
        list(all_tags), list(all_keywords), list(all_headings), get_embedding
    )
    return chunks_to_upsert, list(all_tags), list(all_keywords), list(all_headings), semantic_embedding

def _download_and_validate_pdf(s3_key: str, temp_dir: str = None) -> str:
    """
    Download a PDF from S3 and validate it. Returns the path to the temp file if valid, else None.
    """
    pdf_bytes = read_file_from_s3(s3_key)
    if temp_dir is None:
        temp_dir = tempfile.gettempdir()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=temp_dir) as temp:
        temp.write(pdf_bytes)
        temp.flush()
        temp_path = temp.name
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
    return temp_path

def _process_and_insert_chunks(session, chunks_to_upsert, doc_id, project_id):
    """
    Insert chunk records into the chunk table using SQLAlchemy ORM.
    Expects project_id column to exist in the table. If not, fix your DB migration/init logic.
    """
    chunk_objs = []
    for record in chunks_to_upsert:
        record["document_id"] = doc_id
        record["project_id"] = project_id
        embedding = record["embedding"]
        # Convert numpy ndarray to list for DB insert (not JSON string)
        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()
        chunk_obj = DocumentChunk(
            embedding=embedding,  # assign as list, not JSON string
            chunk_metadata=record["metadata"],
            content=record["content"],
            document_id=doc_id,
            project_id=project_id
        )
        chunk_objs.append(chunk_obj)
    session.add_all(chunk_objs)
    session.commit()

def _upsert_document_record(session, doc_id, all_tags, all_keywords, all_headings, project_id, semantic_embedding=None):
    """
    Upsert the document-level record (tags, keywords, headings, project_id, semantic_embedding) into the documents table using SQLAlchemy ORM.
    """
    # Convert ndarray to list for JSON serialization
    if isinstance(semantic_embedding, np.ndarray):
        semantic_embedding = semantic_embedding.tolist()
    doc = session.query(Document).filter_by(document_id=doc_id).first()
    if doc:
        doc.document_tags = all_tags
        doc.document_keywords = all_keywords
        doc.document_headings = all_headings
        doc.project_id = project_id
        doc.embedding = semantic_embedding
    else:
        doc = Document(
            document_id=doc_id,
            document_tags=all_tags,
            document_keywords=all_keywords,
            document_headings=all_headings,
            project_id=project_id,
            embedding=semantic_embedding
        )
        session.add(doc)
    session.commit()

def load_data(
    s3_key: str,
    base_metadata: Dict[str, Any],
    temp_dir: str = None
) -> str:
    """
    Orchestrate the loading and processing of a document from S3 into the vector store.
    Also records per-method timing metrics in the processing_logs table.
    """
    doc_id = base_metadata.get("document_id") or os.path.basename(s3_key)
    project_id = base_metadata.get("project_id", "")
    print(f"[Worker] Actually processing: doc_id={doc_id}, file_key={s3_key}, project_id={project_id}")
    temp_path = None
    metrics = {}
    # Try to use a shared engine if available, else create locally
    try:
        from src.models.pgvector.vector_db_utils import engine as shared_engine
        engine_to_use = shared_engine
    except ImportError:
        from src.config.settings import get_settings
        settings = get_settings()
        from sqlalchemy import create_engine
        database_url = settings.vector_store_settings.db_url
        if database_url and database_url.startswith('postgresql:'):
            database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
        engine_to_use = create_engine(database_url)
    Session = sessionmaker(bind=engine_to_use)
    session = Session()
    try:
        t0 = time.perf_counter()
        temp_path = _download_and_validate_pdf(s3_key, temp_dir)
        metrics["download_and_validate_pdf"] = time.perf_counter() - t0
        if not temp_path:
            return None
        t1 = time.perf_counter()
        pages = read_as_pages(temp_path)
        metrics["read_as_pages"] = time.perf_counter() - t1
        if not any(page.get("text", "").strip() for page in pages):
            print(f"[WARN] No readable text found in any page of file {s3_key}. Skipping file.")
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
            return None
        t2 = time.perf_counter()
        chunks_to_upsert, all_tags, all_keywords, all_headings, semantic_embedding = chunk_and_embed_pages(pages, base_metadata, s3_key, metrics)
        metrics["chunk_and_embed_pages_time"] = time.perf_counter() - t2
        # Do NOT flatten chunk_and_embed_pages metrics; keep them nested for clarity
        if not chunks_to_upsert:
            print(f"[WARN] No valid text content found in file {s3_key}. Skipping file.")
            return None
        t3 = time.perf_counter()
        _process_and_insert_chunks(session, chunks_to_upsert, doc_id, project_id)
        metrics["process_and_insert_chunks"] = time.perf_counter() - t3
        t4 = time.perf_counter()
        _upsert_document_record(session, doc_id, all_tags, all_keywords, all_headings, project_id, semantic_embedding)
        metrics["upsert_document_record"] = time.perf_counter() - t4
        # Insert metrics into processing_logs table (assumes metrics column exists and is JSONB)
        log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
        if log:
            log.metrics = metrics
            log.status = "success"
        else:
            log = ProcessingLog(document_id=doc_id, project_id=project_id, status="success", metrics=metrics)
            session.add(log)
        session.commit()
        return s3_key
    except Exception as e:
        session.rollback()
        traceback_str = traceback.format_exc()
        print(f"\n[ERROR] Exception processing file:\n  S3 Key: {s3_key}\n  Doc ID: {doc_id}\n  Project ID: {project_id}\n  Error: {e}\nTraceback:\n{traceback_str}\n")
        raise
    finally:
        session.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
