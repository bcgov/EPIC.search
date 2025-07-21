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
from src.config.document_types import get_document_type, resolve_document_type
settings = get_settings()

def build_document_embedding(tags, keywords, headings, document_metadata, embedding_fn):
    """
    Build a semantic embedding for a document from tags, keywords, headings, and document metadata.

    Args:
        tags (list of str): Document tags.
        keywords (list of str): Document keywords.
        headings (list of str): Document headings.
        document_metadata (dict): Document metadata including type, name, etc.
        embedding_fn (callable): Function to generate embedding, e.g. get_embedding.

    Returns:
        embedding (list/np.ndarray): The embedding vector for the document.
        combined_text (str): The text used to generate the embedding.
    """
    tags_sorted = sorted(tags)
    keywords_sorted = sorted(keywords)
    headings_sorted = sorted(headings)
    
    # Extract metadata text for embedding
    metadata_parts = []
    if document_metadata:
        if "document_type" in document_metadata:
            metadata_parts.append(document_metadata["document_type"])
        if "document_name" in document_metadata:
            # Extract meaningful parts from document name (remove file extension)
            doc_name = document_metadata["document_name"]
            if doc_name.endswith('.pdf'):
                doc_name = doc_name[:-4]
            metadata_parts.append(doc_name)
    
    combined_text = (
        " ".join(tags_sorted) + " [SEP] " +
        " ".join(keywords_sorted) + " [SEP] " +
        " ".join(headings_sorted) + " [SEP] " +
        " ".join(metadata_parts)
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
            
            # Add document metadata fields to chunk metadata for performance (avoid joins)
            if base_metadata and "document_metadata" in base_metadata:
                doc_meta = base_metadata["document_metadata"]
                if doc_meta:
                    if "document_type" in doc_meta:
                        chunk_metadata["document_type"] = doc_meta["document_type"]
                    if "document_date" in doc_meta:
                        chunk_metadata["document_date"] = doc_meta["document_date"]
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
    # After all_tags, all_keywords, all_headings are finalized, return them
    # Document-level semantic embedding will be built in load_data with metadata
    return chunks_to_upsert, list(all_tags), list(all_keywords), list(all_headings), None

def _download_and_validate_pdf(s3_key: str, temp_dir: str = None, metrics: dict = None) -> tuple:
    """
    Download a PDF from S3 and validate it. Returns (temp_path, doc_info) where temp_path is the path to the temp file if valid (else None).
    doc_info contains metadata about the document regardless of validation success.
    """
    import pymupdf
    
    doc_info = {
        "s3_key": s3_key,
        "document_name": os.path.basename(s3_key),
        "file_size_bytes": None,
        "pdf_version": None,
        "page_count": None,
        "validation_status": None,
        "validation_reason": None
    }
    
    try:
        pdf_bytes = read_file_from_s3(s3_key)
        doc_info["file_size_bytes"] = len(pdf_bytes)
        
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=temp_dir) as temp:
            temp.write(pdf_bytes)
            temp.flush()
            temp_path = temp.name
        
        # Extract PDF metadata
        try:
            doc = pymupdf.open(temp_path)
            doc_info["metadata"] = doc.metadata
            doc_info["page_count"] = doc.page_count
            doc.close()
        except Exception as pdf_meta_err:
            print(f"[WARN] Could not extract PDF metadata from {s3_key}: {pdf_meta_err}")
        
        is_valid, reason = validate_pdf_file(temp_path, s3_key)
        doc_info["validation_status"] = "valid" if is_valid else "invalid"
        doc_info["validation_reason"] = reason if not is_valid else None
        
        if not is_valid:
            if reason == "scanned_or_image_pdf":
                print(f"[SKIP] File {s3_key} is likely a scanned/image-based PDF (PDF {doc_info.get('pdf_version', 'unknown')}, no extractable text). Marking as failed and deleting temp file.")
            else:
                print(f"[SKIP] File {s3_key} failed PDF validation: {reason}. Deleting temp file.")
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
            return None, doc_info
        
        return temp_path, doc_info
        
    except Exception as e:
        doc_info["validation_status"] = "error"
        doc_info["validation_reason"] = f"Download/processing error: {str(e)}"
        print(f"[ERROR] Failed to download/process {s3_key}: {e}")
        return None, doc_info

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

def _upsert_document_record(session, doc_id, all_tags, all_keywords, all_headings, project_id, semantic_embedding=None, document_metadata=None):
    """
    Upsert the document-level record (tags, keywords, headings, project_id, semantic_embedding, document_metadata) into the documents table using SQLAlchemy ORM.
    """
    # Convert ndarray to list for JSON serialization
    if isinstance(semantic_embedding, np.ndarray):
        semantic_embedding = semantic_embedding.tolist()
    doc = session.query(Document).filter_by(document_id=doc_id).first()
    if doc:
        doc.document_tags = all_tags
        doc.document_keywords = all_keywords
        doc.document_headings = all_headings
        doc.document_metadata = document_metadata
        doc.project_id = project_id
        doc.embedding = semantic_embedding
    else:
        doc = Document(
            document_id=doc_id,
            document_tags=all_tags,
            document_keywords=all_keywords,
            document_headings=all_headings,
            document_metadata=document_metadata,
            project_id=project_id,
            embedding=semantic_embedding
        )
        session.add(doc)
    session.commit()

def extract_document_metadata(api_doc: Dict[str, Any], base_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extract explicit metadata from the API document object and base metadata.
    Only extracts specific fields rather than storing the entire object.
    Uses snake_case for consistency with the rest of the codebase.
    
    Args:
        api_doc: API document object
        base_metadata: Base metadata containing project information
        
    Returns:
        dict: Explicit document metadata with resolved values
    """
    if not api_doc:
        return {}
    
    metadata = {}
    
    # Extract document type with smart resolution - check multiple possible field names
    type_value = None
    
    # Try common field names for document type
    for field_name in ["type", "document_type", "documentType", "doc_type"]:
        if field_name in api_doc and api_doc[field_name]:
            type_value = api_doc[field_name]
            break
    
    document_type, document_type_id = resolve_document_type(type_value)
    metadata["document_type"] = document_type
    metadata["document_type_id"] = document_type_id
    
    # Extract other explicit fields as needed
    if "name" in api_doc:
        metadata["document_name"] = api_doc["name"]
    elif base_metadata and "document_name" in base_metadata:
        metadata["document_name"] = base_metadata["document_name"]
    
    # Extract display name with fallback to document_name without extension
    if "displayName" in api_doc and api_doc["displayName"]:
        metadata["display_name"] = api_doc["displayName"]
    else:
        # Fall back to document_name without file extension
        fallback_name = None
        if "name" in api_doc and api_doc["name"]:
            fallback_name = api_doc["name"]
        elif base_metadata and "document_name" in base_metadata:
            fallback_name = base_metadata["document_name"]
        
        if fallback_name:
            # Remove common file extensions for cleaner display names
            if fallback_name.lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                # Find the last dot and remove extension
                last_dot = fallback_name.rfind('.')
                if last_dot > 0:  # Ensure there's content before the dot
                    fallback_name = fallback_name[:last_dot]
            metadata["display_name"] = fallback_name
    
    if "uploadDate" in api_doc:
        metadata["upload_date"] = api_doc["uploadDate"]
    
    if "fileSize" in api_doc:
        metadata["file_size"] = api_doc["fileSize"]
    
    if "status" in api_doc:
        metadata["document_status"] = api_doc["status"]
    
    if "date" in api_doc:
        metadata["document_date"] = api_doc["date"]
    
    # Add document ID for reference
    if "_id" in api_doc:
        metadata["api_document_id"] = api_doc["_id"]
    
    # Extract project-level fields from base_metadata to avoid duplication in chunks
    if base_metadata:
        if "project_name" in base_metadata:
            metadata["project_name"] = base_metadata["project_name"]
        if "proponent_name" in base_metadata:
            metadata["proponent_name"] = base_metadata["proponent_name"]
        if "doc_internal_name" in base_metadata:
            metadata["document_saved_name"] = base_metadata["doc_internal_name"]
    
    # Add s3_key if available (this will be added during processing)
    # Note: s3_key will be added later in the processing flow
    
    return metadata

def load_data(
    s3_key: str,
    base_metadata: Dict[str, Any],
    temp_dir: str = None,
    api_doc: Dict[str, Any] = None
) -> str:
    """
    Orchestrate the loading and processing of a document from S3 into the vector store.
    Also records per-method timing metrics in the processing_logs table.
    
    Args:
        s3_key: S3 key for the document
        base_metadata: Metadata to attach to chunks
        temp_dir: Temporary directory for file processing
        api_doc: API document object to store as document metadata
    """
    doc_id = base_metadata.get("document_id") or os.path.basename(s3_key)
    project_id = base_metadata.get("project_id", "")
    print(f"[Worker] Actually processing: doc_id={doc_id}, file_key={s3_key}, project_id={project_id}")
    temp_path = None
    metrics = {
        "document_info": None,  # Will be populated with doc metadata regardless of success/failure
    }
    
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
        # Ensure we have basic document info even for early failures
        if not metrics.get("document_info"):
            metrics["document_info"] = {
                "s3_key": s3_key,
                "document_name": os.path.basename(s3_key)
            }
        
        # Add document_name and display_name from API if available, even before processing
        api_derived_names = {}
        if api_doc:
            basic_metadata = extract_document_metadata(api_doc, base_metadata)
            if basic_metadata.get("document_name"):
                api_derived_names["document_name"] = basic_metadata["document_name"]
                metrics["document_info"]["document_name"] = basic_metadata["document_name"]
            if basic_metadata.get("display_name"):
                api_derived_names["display_name"] = basic_metadata["display_name"]
                metrics["document_info"]["display_name"] = basic_metadata["display_name"]
        
        t0 = time.perf_counter()
        temp_path, doc_info = _download_and_validate_pdf(s3_key, temp_dir, metrics)
        metrics["download_and_validate_pdf"] = time.perf_counter() - t0
        
        # Merge doc_info but preserve API-derived names if they exist
        if doc_info:
            metrics["document_info"].update(doc_info)
            # Restore API-derived names if they were better than the S3 basename
            if api_derived_names.get("document_name"):
                metrics["document_info"]["document_name"] = api_derived_names["document_name"]
            if api_derived_names.get("display_name"):
                metrics["document_info"]["display_name"] = api_derived_names["display_name"]
        
        if not temp_path:
            # Log failure with document info in metrics
            log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
            if log:
                log.metrics = metrics
                log.status = "failure"
            else:
                log = ProcessingLog(document_id=doc_id, project_id=project_id, status="failure", metrics=metrics)
                session.add(log)
            session.commit()
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
            
            # Log failure with document info
            log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
            if log:
                log.metrics = metrics
                log.status = "failure"
            else:
                log = ProcessingLog(document_id=doc_id, project_id=project_id, status="failure", metrics=metrics)
                session.add(log)
            session.commit()
            return None

        # Extract explicit metadata from API document early so it can be included in chunk metadata
        document_metadata = extract_document_metadata(api_doc, base_metadata)
        
        # Add document_name and display_name to document_info in metrics for processing logs
        if metrics.get("document_info"):
            metrics["document_info"]["document_name"] = document_metadata.get("document_name")
            metrics["document_info"]["display_name"] = document_metadata.get("display_name")
        
        # Add s3_key to document metadata
        document_metadata["s3_key"] = s3_key
        
        # Add document metadata to base_metadata for inclusion in chunks (keep duplication for performance)
        base_metadata_with_doc = {**base_metadata, "document_metadata": document_metadata}

        t2 = time.perf_counter()
        chunks_to_upsert, all_tags, all_keywords, all_headings, _ = chunk_and_embed_pages(pages, base_metadata_with_doc, s3_key, metrics)
        metrics["chunk_and_embed_pages_time"] = time.perf_counter() - t2
        
        # Build document-level semantic embedding with metadata
        semantic_embedding, _ = build_document_embedding(
            list(all_tags), list(all_keywords), list(all_headings), document_metadata, get_embedding
        )
        
        # Do NOT flatten chunk_and_embed_pages metrics; keep them nested for clarity
        if not chunks_to_upsert:
            print(f"[WARN] No valid text content found in file {s3_key}. Skipping file.")
            # Log failure with document info
            log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
            if log:
                log.metrics = metrics
                log.status = "failure"
            else:
                log = ProcessingLog(document_id=doc_id, project_id=project_id, status="failure", metrics=metrics)
                session.add(log)
            session.commit()
            return None

        t3 = time.perf_counter()
        _process_and_insert_chunks(session, chunks_to_upsert, doc_id, project_id)
        metrics["process_and_insert_chunks"] = time.perf_counter() - t3

        t4 = time.perf_counter()
        _upsert_document_record(session, doc_id, all_tags, all_keywords, all_headings, project_id, semantic_embedding, document_metadata)
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
        
        # Ensure we have basic document info even for complete failures
        if not metrics.get("document_info"):
            metrics["document_info"] = {
                "s3_key": s3_key,
                "document_name": os.path.basename(s3_key)
            }
        
        # Add document_name and display_name from API if available
        if api_doc:
            try:
                basic_metadata = extract_document_metadata(api_doc, base_metadata)
                if basic_metadata.get("document_name"):
                    metrics["document_info"]["document_name"] = basic_metadata["document_name"]
                if basic_metadata.get("display_name"):
                    metrics["document_info"]["display_name"] = basic_metadata["display_name"]
            except Exception as meta_err:
                print(f"[WARN] Could not extract basic metadata for failure logging: {meta_err}")
        
        # Log failure with document info and exception details
        metrics["error"] = str(e)
        metrics["traceback"] = traceback_str
        try:
            log = session.query(ProcessingLog).filter_by(document_id=doc_id, project_id=project_id).first()
            if log:
                log.metrics = metrics
                log.status = "failure"
            else:
                log = ProcessingLog(document_id=doc_id, project_id=project_id, status="failure", metrics=metrics)
                session.add(log)
            session.commit()
        except Exception as log_err:
            print(f"[ERROR] Failed to log failure metrics: {log_err}")
        
        raise
    finally:
        session.close()
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_err:
                print(f"[WARN] Could not delete temp file {temp_path}: {cleanup_err}")
