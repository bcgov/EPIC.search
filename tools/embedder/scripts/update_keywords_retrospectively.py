#!/usr/bin/env python3
"""
Script to retrospectively update keywords for successfully embedded documents.

This script:
1. Connects to the database and finds all successful documents
2. Excludes documents that used Azure Vision service (as they have custom keywords)
3. Re-extracts keywords for document chunks using the configured KEYWORD_EXTRACTION_MODE
4. Updates chunk metadata with new keywords
5. Consolidates document keywords into a unique list
6. Regenerates and overrides document-level embeddings (from tags, keywords, headings)

Usage:
    python scripts/update_keywords_retrospectively.py [--project_id PROJECT_ID] [--mode MODE] [--dry_run] [--limit LIMIT]

Arguments:
    --project_id: Optional project ID to limit processing to specific project
    --mode: Keyword extraction mode override (standard, fast, simplified). If not provided, uses KEYWORD_EXTRACTION_MODE from .env
    --dry_run: Show what would be updated without making changes
    --limit: Limit number of documents to process (for testing)
"""

import os
import sys
import argparse
import time
from typing import List, Set, Tuple, Optional
from datetime import datetime

# Add the project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

# Import project modules
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
from src.models.pgvector.vector_models import Document, DocumentChunk, ProcessingLog
from src.models import get_session
from src.services.embedding import get_embedding
from src.services.loader import build_document_embedding

# Import keyword extraction factory
from src.services.keywords.keyword_factory import extract_keywords_from_chunks, get_extraction_mode_info, list_available_modes

settings = get_settings()

def get_keyword_extraction_function(mode: str):
    """Get the appropriate keyword extraction function based on mode using the factory pattern."""
    available_modes = list_available_modes()
    if mode not in available_modes:
        raise ValueError(f"Unknown keyword extraction mode: {mode}. Valid modes: {', '.join(available_modes)}")
    
    # Temporarily override the settings mode for this extraction
    original_mode = settings.multi_processing_settings.keyword_extraction_mode
    settings.multi_processing_settings.keyword_extraction_mode = mode
    
    def extraction_wrapper(chunks, document_id=None):
        try:
            return extract_keywords_from_chunks(chunks, document_id)
        finally:
            # Restore original mode
            settings.multi_processing_settings.keyword_extraction_mode = original_mode
    
    return extraction_wrapper


def is_azure_vision_document(session, document_id: str, project_id: str) -> bool:
    """
    Check if a document used Azure Vision for processing by examining processing logs.
    
    Azure Vision documents have custom keywords generated from image analysis,
    so we should exclude them from keyword updates.
    
    Args:
        session: SQLAlchemy session
        document_id: Document ID to check
        project_id: Project ID for the document
        
    Returns:
        bool: True if the document used Azure Vision, False otherwise
    """
    try:
        # Check processing logs for image analysis usage
        log = session.query(ProcessingLog).filter_by(
            document_id=document_id,
            project_id=project_id
        ).first()
        
        if not log or not log.metrics:
            return False
            
        metrics = log.metrics
        
        # Check for image analysis in processing summary
        if 'image_processing_summary' in metrics:
            image_summary = metrics['image_processing_summary']
            if 'image_analysis' in image_summary:
                method = image_summary['image_analysis'].get('method', '')
                return method == 'azure_computer_vision'
        
        # Check for image analysis in document info / ocr processing
        if 'document_info' in metrics and 'ocr_processing' in metrics['document_info']:
            ocr_info = metrics['document_info']['ocr_processing']
            if ocr_info.get('image_analysis_attempted') and ocr_info.get('image_analysis_successful'):
                method = ocr_info.get('image_analysis_method', '')
                return method == 'azure_computer_vision'
        
        # Check for specific processing methods that indicate image analysis
        if 'document_info' in metrics:
            doc_info = metrics['document_info']
            processing_method = doc_info.get('processing_method', '')
            if processing_method in ['image_analysis_processed', 'image_pdf_analysis_processed']:
                # Additional check for Azure Vision method if available
                if 'image_processing_summary' in doc_info:
                    method = doc_info['image_processing_summary'].get('image_analysis', {}).get('method', '')
                    return method == 'azure_computer_vision'
                return True  # Assume Azure Vision if image analysis was used
        
        return False
        
    except Exception as e:
        print(f"[WARN] Error checking Azure Vision status for {document_id}: {e}")
        return False


def get_successful_documents(session, project_id: Optional[str] = None, limit: Optional[int] = None) -> List[Tuple[str, str]]:
    """
    Get all successfully processed documents from the database.
    
    Returns list of (document_id, project_id) tuples.
    """
    query = session.query(ProcessingLog.document_id, ProcessingLog.project_id).filter(
        ProcessingLog.status == 'success'
    )
    
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    # Get unique documents (in case there are multiple processing logs)
    query = query.distinct()
    
    if limit:
        query = query.limit(limit)
    
    results = query.all()
    print(f"Found {len(results)} successfully processed documents")
    
    if project_id:
        print(f"Filtered to project: {project_id}")
    
    return results


def get_document_chunks(session, document_id: str) -> List[DocumentChunk]:
    """Get all chunks for a document."""
    chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    return chunks


def get_document_record(session, document_id: str) -> Optional[Document]:
    """Get the document record."""
    return session.query(Document).filter(Document.document_id == document_id).first()


def update_chunk_keywords(session, chunks: List[DocumentChunk], keyword_extraction_fn, document_id: str = None, dry_run: bool = False) -> Tuple[Set[str], float]:
    """
    Update keywords for all chunks using the specified extraction function.
    
    Returns tuple of (set of all unique keywords found, keyword extraction time).
    """
    if not chunks:
        return set(), 0.0
    
    # Convert chunks to the format expected by keyword extraction functions
    chunk_dicts = []
    for chunk in chunks:
        chunk_dict = {
            'content': chunk.content,
            'metadata': chunk.chunk_metadata.copy() if chunk.chunk_metadata else {}
        }
        chunk_dicts.append(chunk_dict)
    
    print(f"  Extracting keywords for {len(chunk_dicts)} chunks...")
    
    # Extract keywords with timing
    start_time = time.perf_counter()
    updated_chunks, all_keywords = keyword_extraction_fn(chunk_dicts, document_id=document_id)
    keyword_extraction_time = time.perf_counter() - start_time
    
    print(f"  Extracted {len(all_keywords)} unique keywords: {sorted(list(all_keywords))[:10]}... (took {keyword_extraction_time:.3f}s)")
    
    if not dry_run:
        # Update chunk metadata with new keywords
        for i, chunk in enumerate(chunks):
            if i < len(updated_chunks):
                chunk.chunk_metadata = updated_chunks[i]['metadata']
        
        # Commit chunk updates
        session.commit()
        print(f"  Updated {len(chunks)} chunks with new keywords")
    else:
        print(f"  [DRY RUN] Would update {len(chunks)} chunks with new keywords")
    
    return all_keywords, keyword_extraction_time


def consolidate_document_keywords(all_keywords: Set[str]) -> List[str]:
    """
    Consolidate keywords into a unique sorted list for the document.
    """
    return sorted(list(all_keywords))


def update_document_embedding(session, document: Document, consolidated_keywords: List[str], dry_run: bool = False) -> None:
    """
    Regenerate and update the document-level embedding from tags, keywords, and headings.
    """
    # Get existing tags and headings
    tags = document.document_tags or []
    headings = document.document_headings or []
    metadata = document.document_metadata or {}
    
    print(f"  Regenerating document embedding with {len(tags)} tags, {len(consolidated_keywords)} keywords, {len(headings)} headings")
    
    if not dry_run:
        # Build new embedding
        new_embedding, combined_text = build_document_embedding(
            tags=tags,
            keywords=consolidated_keywords,
            headings=headings,
            document_metadata=metadata,
            embedding_fn=get_embedding
        )
        
        # Update document record
        document.document_keywords = consolidated_keywords
        document.embedding = new_embedding
        
        session.commit()
        print(f"  Updated document embedding (combined text length: {len(combined_text)})")
    else:
        print(f"  [DRY RUN] Would update document embedding with {len(consolidated_keywords)} keywords")


def update_processing_log_metadata(session, document_id: str, project_id: str, keyword_extraction_time: float, 
                                  processed_chunks: int, total_keywords: int, dry_run: bool = False) -> None:
    """
    Update the processing log metadata to include retrospective keyword update information.
    """
    if dry_run:
        print(f"  [DRY RUN] Would update processing log with keyword extraction time: {keyword_extraction_time:.3f}s")
        return
        
    try:
        log = session.query(ProcessingLog).filter_by(
            document_id=document_id,
            project_id=project_id
        ).first()
        
        if not log:
            print(f"  [WARN] No processing log found for {document_id}")
            return
            
        # Ensure metrics exists
        if not log.metrics:
            log.metrics = {}
        
        # Add retrospective keyword update information
        if 'retrospective_updates' not in log.metrics:
            log.metrics['retrospective_updates'] = {}
            
        # Update keyword extraction metrics
        log.metrics['retrospective_updates']['keyword_update'] = {
            'updated_at': datetime.now().isoformat(),
            'chunks_processed': processed_chunks,
            'total_keywords_extracted': total_keywords,
            'keyword_extraction_time': keyword_extraction_time,
            'extraction_mode': settings.multi_processing_settings.keyword_extraction_mode
        }
        
        # Update the original keyword extraction time if it exists
        if 'chunk_and_embed_pages' in log.metrics:
            original_time = log.metrics['chunk_and_embed_pages'].get('get_keywords_time_total', 0.0)
            log.metrics['chunk_and_embed_pages']['get_keywords_time_total_retrospective'] = keyword_extraction_time
            log.metrics['chunk_and_embed_pages']['get_keywords_time_original'] = original_time
        
        session.commit()
        print(f"  Updated processing log metadata (keyword extraction: {keyword_extraction_time:.3f}s)")
        
    except Exception as e:
        print(f"  [WARN] Failed to update processing log metadata: {e}")
        session.rollback()


def process_document(session, document_id: str, project_id: str, keyword_extraction_fn, dry_run: bool = False) -> bool:
    """
    Process a single document to update its keywords and embedding.
    
    Returns True if document was processed, False if skipped.
    """
    print(f"\nProcessing document: {document_id}")
    
    # Get document chunks
    chunks = get_document_chunks(session, document_id)
    if not chunks:
        print(f"  No chunks found for document {document_id}, skipping")
        return False
    
    # Check if document used Azure Vision service
    if is_azure_vision_document(session, document_id, project_id):
        print(f"  Document {document_id} used Azure Vision service, skipping")
        return False
    
    # Get document record
    document = get_document_record(session, document_id)
    if not document:
        print(f"  No document record found for {document_id}, skipping")
        return False
    
    try:
        # Update chunk keywords
        all_keywords, keyword_extraction_time = update_chunk_keywords(session, chunks, keyword_extraction_fn, document_id, dry_run)
        
        # Consolidate document keywords
        consolidated_keywords = consolidate_document_keywords(all_keywords)
        
        # Update document embedding
        update_document_embedding(session, document, consolidated_keywords, dry_run)
        
        # Update processing log metadata with timing information
        update_processing_log_metadata(session, document_id, project_id, keyword_extraction_time, 
                                     len(chunks), len(all_keywords), dry_run)
        
        print(f"  ✓ Successfully processed document {document_id}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing document {document_id}: {str(e)}")
        session.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description="Retrospectively update keywords for embedded documents")
    parser.add_argument("--project_id", help="Optional project ID to limit processing")
    parser.add_argument("--mode", choices=["standard", "fast", "simplified"], 
                       help="Keyword extraction mode (overrides KEYWORD_EXTRACTION_MODE from .env)")
    parser.add_argument("--dry_run", action="store_true", 
                       help="Show what would be updated without making changes")
    parser.add_argument("--limit", type=int, 
                       help="Limit number of documents to process (for testing)")
    
    args = parser.parse_args()
    
    # Determine keyword extraction mode
    mode = args.mode or settings.multi_processing_settings.keyword_extraction_mode
    print(f"Using keyword extraction mode: {mode}")
    
    # Get keyword extraction function
    try:
        keyword_extraction_fn = get_keyword_extraction_function(mode)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    if args.dry_run:
        print("DRY RUN MODE: No changes will be made to the database")
    
    print(f"Database URL: {settings.vector_store_settings.db_url}")
    
    # Get database session
    session = get_session()
    
    try:
        # Get successful documents
        documents = get_successful_documents(session, args.project_id, args.limit)
        
        if not documents:
            print("No documents found to process")
            return 0
        
        processed_count = 0
        skipped_count = 0
        
        start_time = datetime.now()
        
        for i, (document_id, project_id) in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] Processing {document_id} (project: {project_id})")
            
            success = process_document(session, document_id, project_id, keyword_extraction_fn, args.dry_run)
            
            if success:
                processed_count += 1
            else:
                skipped_count += 1
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n" + "="*60)
        print(f"SUMMARY")
        print(f"="*60)
        print(f"Total documents: {len(documents)}")
        print(f"Processed: {processed_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Duration: {duration}")
        print(f"Mode: {mode}")
        
        if args.dry_run:
            print(f"DRY RUN: No actual changes were made")
        
    finally:
        session.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
