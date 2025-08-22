#!/usr/bin/env python3
"""
Script to retrospectively update tags for successfully embedded documents.

This script:
1. Connects to the database and finds all successful documents
2. Excludes documents that used Azure Vision service (as they have custom tags)
3. Re-extracts tags for document chunks using the current TAGS list
4. Updates chunk metadata with new tags
5. Consolidates document tags into a unique list
6. Regenerates and overrides document-level embeddings (from tags, keywords, headings)

Usage:
    python scripts/update_tags_retrospectively.py [--project_id PROJECT_ID] [--dry_run] [--limit LIMIT]

Arguments:
    --project_id: Optional project ID to limit processing to specific project
    --dry_run: Show what would be updated without making changes
    --limit: Limit number of documents to process (for testing)
"""

import os
import sys
import argparse
import time
import datetime
from typing import List, Set, Tuple, Optional

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

# Import tag extraction
from src.services.tags.tag_extractor import extract_tags_from_chunks
from src.services.tags.tags_list import get_tags_count

settings = get_settings()


def check_azure_vision_usage(processing_log: ProcessingLog) -> bool:
    """
    Check if the document was processed using Azure Vision service.
    
    Documents processed with Azure Vision have custom tags and should be excluded
    from retrospective tag updates to avoid overriding specialized analysis.
    """
    if not processing_log.metrics:
        return False
        
    try:
        metrics = processing_log.metrics
        document_id = processing_log.document_id
        
        # Check for image analysis summary in processing metrics
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
    
    return results


def process_document_tags(session, document_id: str, project_id: str, dry_run: bool = False) -> Tuple[Set[str], float]:
    """
    Re-extract tags for a document and update chunk metadata.
    
    Returns:
        Tuple of (all_tags_set, tag_extraction_time)
    """
    print(f"Processing document: {document_id}")
    
    # Get document and chunks
    document = session.query(Document).filter(Document.document_id == document_id).first()
    if not document:
        raise ValueError(f"Document {document_id} not found")
    
    chunks = session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    if not chunks:
        print(f"  No chunks found for document {document_id}")
        return set(), 0.0
    
    print(f"  Extracting tags for {len(chunks)} chunks...")
    
    # Prepare chunk data for tag extraction
    chunk_dicts = []
    for i, chunk in enumerate(chunks):
        chunk_dict = {
            'id': i,  # Add an ID for tracking
            'content': chunk.content,
            'metadata': chunk.chunk_metadata or {}
        }
        chunk_dicts.append(chunk_dict)
    
    # Extract tags using the current tag extraction system
    start_time = time.time()
    tag_results = extract_tags_from_chunks(chunk_dicts, document_id)
    tag_extraction_time = time.time() - start_time
    
    # Extract all unique tags from the results
    if tag_results and isinstance(tag_results, dict):
        all_tags = set(tag_results.get("all_matches", []))
        chunk_id_to_tags = {chunk["chunk_id"]: chunk["all_matches"] for chunk in tag_results.get("chunks", [])}
    else:
        all_tags = set()
        chunk_id_to_tags = {}
    
    print(f"  Extracted {len(all_tags)} unique tags: {sorted(list(all_tags))[:10]}{'...' if len(all_tags) > 10 else ''} (took {tag_extraction_time:.3f}s)")
    
    # Update chunks with new tag metadata
    if not dry_run:
        for i, chunk in enumerate(chunks):
            # Update chunk metadata with new tags
            if chunk.chunk_metadata is None:
                chunk.chunk_metadata = {}
            
            # Get tags for this chunk by ID
            chunk_tags = chunk_id_to_tags.get(i, [])
            chunk.chunk_metadata['tags'] = chunk_tags
        
        # Commit chunk updates
        session.commit()
        print(f"  Updated {len(chunks)} chunks with new tags")
    else:
        print(f"  [DRY RUN] Would update {len(chunks)} chunks with new tags")
    
    return all_tags, tag_extraction_time


def consolidate_document_tags(all_tags: Set[str]) -> List[str]:
    """
    Consolidate tags into a unique sorted list for the document.
    """
    return sorted(list(all_tags))


def update_document_embedding(session, document: Document, consolidated_tags: List[str], dry_run: bool = False) -> None:
    """
    Regenerate and update the document-level embedding from tags, keywords, and headings.
    """
    # Get existing keywords and headings
    keywords = document.document_keywords or []
    headings = document.document_headings or []
    metadata = document.document_metadata or {}
    
    print(f"  Regenerating document embedding with {len(consolidated_tags)} tags, {len(keywords)} keywords, {len(headings)} headings")
    
    if not dry_run:
        # Build new embedding
        new_embedding, combined_text = build_document_embedding(
            tags=consolidated_tags,
            keywords=keywords,
            headings=headings,
            document_metadata=metadata,
            embedding_fn=get_embedding
        )
        
        # Update document record
        document.document_tags = consolidated_tags
        document.embedding = new_embedding
        
        session.commit()
        print(f"  Updated document embedding (combined text length: {len(combined_text)})")
    else:
        print(f"  [DRY RUN] Would update document embedding with {len(consolidated_tags)} tags")


def update_processing_log_metadata(session, document_id: str, project_id: str, tag_extraction_time: float, 
                                  processed_chunks: int, total_tags: int, dry_run: bool = False) -> None:
    """
    Update processing log metadata with tag extraction timing information.
    """
    if dry_run:
        print(f"  [DRY RUN] Would update processing log metadata (tag extraction: {tag_extraction_time:.3f}s)")
        return
    
    # Get the most recent processing log for this document
    processing_log = session.query(ProcessingLog).filter(
        ProcessingLog.document_id == document_id,
        ProcessingLog.project_id == project_id,
        ProcessingLog.status == 'success'
    ).order_by(ProcessingLog.processed_at.desc()).first()
    
    if processing_log and processing_log.metrics:
        # Update metrics with tag extraction timing
        if 'retrospective_updates' not in processing_log.metrics:
            processing_log.metrics['retrospective_updates'] = {}
        
        processing_log.metrics['retrospective_updates']['tag_extraction'] = {
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'extraction_time_seconds': tag_extraction_time,
            'chunks_processed': processed_chunks,
            'total_tags_extracted': total_tags,
            'tags_list_version': get_tags_count()  # Track the version by tag count
        }
        
        session.commit()
        print(f"  Updated processing log metadata (tag extraction: {tag_extraction_time:.3f}s)")


def main():
    parser = argparse.ArgumentParser(description='Retrospectively update tags for embedded documents')
    parser.add_argument('--project_id', type=str, help='Optional project ID to limit processing')
    parser.add_argument('--dry_run', action='store_true', help='Show what would be updated without making changes')
    parser.add_argument('--limit', type=int, help='Limit number of documents to process (for testing)')
    
    args = parser.parse_args()
    
    print(f"Tag extraction system info:")
    print(f"Current tags list: {get_tags_count()} tags available")
    print(f"Database URL: {settings.vector_store_settings.db_url}")
    
    # Create database session
    session = get_session()
    
    try:
        # Get documents to process
        documents = get_successful_documents(session, args.project_id, args.limit)
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN MODE - No changes will be made")
        
        processed_count = 0
        skipped_count = 0
        start_time = time.time()
        
        for i, (document_id, project_id) in enumerate(documents, 1):
            print(f"\n[{i}/{len(documents)}] Processing {document_id} (project: {project_id})")
            
            try:
                # Check if document used Azure Vision (skip if so)
                processing_log = session.query(ProcessingLog).filter(
                    ProcessingLog.document_id == document_id,
                    ProcessingLog.project_id == project_id,
                    ProcessingLog.status == 'success'
                ).order_by(ProcessingLog.processed_at.desc()).first()
                
                if processing_log and check_azure_vision_usage(processing_log):
                    print(f"  ⏭️  Skipping document processed with Azure Vision service")
                    skipped_count += 1
                    continue
                
                # Process document tags
                all_tags, tag_extraction_time = process_document_tags(session, document_id, project_id, args.dry_run)
                
                # Consolidate tags
                consolidated_tags = consolidate_document_tags(all_tags)
                
                # Get document for embedding update
                document = session.query(Document).filter(Document.document_id == document_id).first()
                if document:
                    # Update document embedding
                    update_document_embedding(session, document, consolidated_tags, args.dry_run)
                    
                    # Update processing log metadata
                    chunks_count = session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).count()
                    update_processing_log_metadata(session, document_id, project_id, tag_extraction_time, 
                                                 chunks_count, len(consolidated_tags), args.dry_run)
                
                processed_count += 1
                print(f"  ✓ Successfully processed document {document_id}")
                
            except Exception as e:
                print(f"  ❌ Error processing document {document_id}: {e}")
                import traceback
                traceback.print_exc()
        
        total_time = time.time() - start_time
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total documents: {len(documents)}")
        print(f"Processed: {processed_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Duration: {str(datetime.datetime.fromtimestamp(total_time) - datetime.datetime.fromtimestamp(0)).split('.')[0]}")
        print(f"Tags list: {get_tags_count()} tags")
        
        if args.dry_run:
            print(f"\n🔍 This was a DRY RUN - no changes were made to the database")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()
