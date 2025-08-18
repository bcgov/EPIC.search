from src.models import get_session
from src.models.pgvector.vector_models import ProcessingLog, DocumentChunk, Document
from sqlalchemy import text

"""
Repair Service module for identifying and fixing inconsistent document states.

This module provides functionality to detect and repair documents that are in 
inconsistent states due to interrupted processing, partial failures, or other issues.
"""

def analyze_repair_candidates(project_id=None):
    """
    Analyze the database to identify documents that need repair.
    
    Identifies several types of inconsistent states:
    1. Documents with chunks but marked as failed
    2. Documents that started processing but never got a final status
    3. Orphaned chunks without corresponding document records
    4. Documents marked as successful but missing expected data
    
    Args:
        project_id (str, optional): Filter by project ID. If None, analyzes all projects.
        
    Returns:
        dict: Dictionary containing lists of documents that need repair, categorized by issue type
    """
    session = get_session()
    
    try:
        repair_candidates = {
            'partial_failures': [],      # Failed status but has chunks
            'incomplete_processing': [], # No final status but may have chunks
            'orphaned_chunks': [],       # Chunks without document records
            'missing_document_records': [], # Chunks exist but no document record
            'inconsistent_success': []   # Success status but missing chunks/document
        }
        
        # Add project filter if specified
        pl_project_filter = ""
        dc_project_filter = ""
        d_project_filter = ""
        if project_id:
            pl_project_filter = f"AND pl.project_id = '{project_id}'"
            dc_project_filter = f"AND dc.project_id = '{project_id}'"
            d_project_filter = f"AND d.project_id = '{project_id}'"
        
        # 1. Find documents with chunks but marked as failed (partial failures)
        partial_failure_query = text(f"""
            SELECT DISTINCT pl.document_id, pl.project_id, pl.status, pl.processed_at,
                   COUNT(dc.id) as chunk_count,
                   pl.metrics->'document_info'->>'document_name' as doc_name
            FROM processing_logs pl
            JOIN document_chunks dc ON pl.document_id = dc.document_id
            WHERE pl.status = 'failure' {pl_project_filter}
            GROUP BY pl.document_id, pl.project_id, pl.status, pl.processed_at, pl.metrics
            ORDER BY pl.processed_at DESC
        """)
        
        result = session.execute(partial_failure_query)
        for row in result:
            repair_candidates['partial_failures'].append({
                'document_id': row.document_id,
                'project_id': row.project_id,
                'status': row.status,
                'processed_at': row.processed_at,
                'chunk_count': row.chunk_count,
                'document_name': row.doc_name,
                'issue': 'Has chunks but marked as failed - likely interrupted during final status update'
            })
        
        # 2. Find documents that have chunks but no processing log (incomplete processing)
        incomplete_query = text(f"""
            SELECT DISTINCT dc.document_id, dc.project_id, COUNT(dc.id) as chunk_count,
                   dc.metadata->>'document_name' as doc_name
            FROM document_chunks dc
            LEFT JOIN processing_logs pl ON dc.document_id = pl.document_id AND dc.project_id = pl.project_id
            WHERE pl.document_id IS NULL {dc_project_filter}
            GROUP BY dc.document_id, dc.project_id, dc.metadata
            ORDER BY dc.document_id
        """)
        
        result = session.execute(incomplete_query)
        for row in result:
            repair_candidates['incomplete_processing'].append({
                'document_id': row.document_id,
                'project_id': row.project_id,
                'chunk_count': row.chunk_count,
                'document_name': row.doc_name,
                'issue': 'Has chunks but no processing log - processing was interrupted'
            })
        
        # 3. Find orphaned chunks (chunks without document records in documents table)
        orphaned_chunks_query = text(f"""
            SELECT DISTINCT dc.document_id, dc.project_id, COUNT(dc.id) as chunk_count,
                   dc.metadata->>'document_name' as doc_name
            FROM document_chunks dc
            LEFT JOIN documents d ON dc.document_id = d.document_id
            WHERE d.document_id IS NULL {dc_project_filter}
            GROUP BY dc.document_id, dc.project_id, dc.metadata
            ORDER BY dc.document_id
        """)
        
        result = session.execute(orphaned_chunks_query)
        for row in result:
            repair_candidates['orphaned_chunks'].append({
                'document_id': row.document_id,
                'project_id': row.project_id,
                'chunk_count': row.chunk_count,
                'document_name': row.doc_name,
                'issue': 'Chunks exist but no document record - document processing incomplete'
            })
        
        # 4. Find successful documents with no chunks (should have been processed)
        missing_chunks_query = text(f"""
            SELECT pl.document_id, pl.project_id, pl.status, pl.processed_at,
                   pl.metrics->'document_info'->>'document_name' as doc_name
            FROM processing_logs pl
            LEFT JOIN document_chunks dc ON pl.document_id = dc.document_id AND pl.project_id = dc.project_id
            WHERE pl.status = 'success' 
            AND dc.document_id IS NULL {pl_project_filter}
            ORDER BY pl.processed_at DESC
        """)
        
        result = session.execute(missing_chunks_query)
        for row in result:
            repair_candidates['inconsistent_success'].append({
                'document_id': row.document_id,
                'project_id': row.project_id,
                'status': row.status,
                'processed_at': row.processed_at,
                'document_name': row.doc_name,
                'issue': 'Marked as successful but no chunks found - data may have been lost'
            })
        
        return repair_candidates
        
    finally:
        session.close()

def cleanup_document_data(document_id: str, project_id: str):
    """
    Clean up all data for a document before reprocessing.
    
    Removes chunks, document records, and processing logs for the specified document
    to ensure a clean reprocessing attempt.
    
    Args:
        document_id (str): The document ID to clean up
        project_id (str): The project ID the document belongs to
        
    Returns:
        dict: Summary of what was cleaned up
    """
    session = get_session()
    
    try:
        cleanup_summary = {
            'chunks_deleted': 0,
            'document_records_deleted': 0,
            'processing_logs_deleted': 0
        }
        
        # Delete chunks
        chunks_deleted = session.query(DocumentChunk).filter_by(
            document_id=document_id, 
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['chunks_deleted'] = chunks_deleted
        
        # Delete document record
        docs_deleted = session.query(Document).filter_by(
            document_id=document_id
        ).delete(synchronize_session=False)
        cleanup_summary['document_records_deleted'] = docs_deleted
        
        # Delete processing logs
        logs_deleted = session.query(ProcessingLog).filter_by(
            document_id=document_id,
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['processing_logs_deleted'] = logs_deleted
        
        session.commit()
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def cleanup_document_content_for_retry(document_id: str, project_id: str):
    """
    Clean up document content (chunks and records) for retry processing.
    
    This removes chunks and document records but preserves processing logs
    so that the retry status is maintained until successful reprocessing.
    
    Args:
        document_id (str): The document ID to clean up
        project_id (str): The project ID the document belongs to
        
    Returns:
        dict: Summary of what was cleaned up
    """
    session = get_session()
    
    try:
        cleanup_summary = {
            'chunks_deleted': 0,
            'document_records_deleted': 0,
            'processing_logs_preserved': 0
        }
        
        # Delete chunks
        chunks_deleted = session.query(DocumentChunk).filter_by(
            document_id=document_id, 
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['chunks_deleted'] = chunks_deleted
        
        # Delete document record
        docs_deleted = session.query(Document).filter_by(
            document_id=document_id
        ).delete(synchronize_session=False)
        cleanup_summary['document_records_deleted'] = docs_deleted
        
        # Count processing logs (preserved, not deleted)
        logs_count = session.query(ProcessingLog).filter_by(
            document_id=document_id,
            project_id=project_id
        ).count()
        cleanup_summary['processing_logs_preserved'] = logs_count
        
        session.commit()
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def cleanup_project_data(project_id: str):
    """
    Clean up ALL data for a project (complete reset).
    
    Removes all chunks, document records, and processing logs for the specified project
    to enable a complete fresh reprocessing.
    
    Args:
        project_id (str): The project ID to completely clean up
        
    Returns:
        dict: Summary of what was cleaned up
    """
    session = get_session()
    
    try:
        cleanup_summary = {
            'chunks_deleted': 0,
            'document_records_deleted': 0,
            'processing_logs_deleted': 0,
            'project_id': project_id
        }
        
        print(f"[RESET] Starting complete cleanup for project {project_id}")
        
        # Delete all chunks for this project
        chunks_deleted = session.query(DocumentChunk).filter_by(
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['chunks_deleted'] = chunks_deleted
        print(f"[RESET] Deleted {chunks_deleted} document chunks")
        
        # Delete all document records for this project (direct filter, no join needed)
        docs_deleted = session.query(Document).filter_by(
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['document_records_deleted'] = docs_deleted
        print(f"[RESET] Deleted {docs_deleted} document records")
        
        # Delete all processing logs for this project
        logs_deleted = session.query(ProcessingLog).filter_by(
            project_id=project_id
        ).delete(synchronize_session=False)
        cleanup_summary['processing_logs_deleted'] = logs_deleted
        print(f"[RESET] Deleted {logs_deleted} processing log entries")
        
        session.commit()
        
        total_deleted = cleanup_summary['chunks_deleted'] + cleanup_summary['document_records_deleted'] + cleanup_summary['processing_logs_deleted']
        print(f"[RESET] Project {project_id} cleanup complete: {total_deleted} total records deleted")
        
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        print(f"[RESET] Error during project cleanup: {e}")
        raise e
    finally:
        session.close()

def get_repair_candidates_for_processing(project_id=None):
    """
    Get a list of documents that need repair, formatted for processing.
    
    Returns documents that should be reprocessed after cleanup, excluding
    cases that are just informational (like orphaned chunks that need cleanup only).
    
    Args:
        project_id (str, optional): Filter by project ID
        
    Returns:
        list: List of document dictionaries that need reprocessing
    """
    repair_analysis = analyze_repair_candidates(project_id)
    
    # Combine categories that need reprocessing
    candidates_for_reprocessing = []
    
    # Add partial failures (failed but has chunks - needs cleanup and reprocess)
    for doc in repair_analysis['partial_failures']:
        candidates_for_reprocessing.append({
            'document_id': doc['document_id'],
            'project_id': doc['project_id'],
            'document_name': doc['document_name'],
            'repair_reason': 'partial_failure',
            'description': doc['issue']
        })
    
    # Add incomplete processing (has chunks but no log - needs cleanup and reprocess)  
    for doc in repair_analysis['incomplete_processing']:
        candidates_for_reprocessing.append({
            'document_id': doc['document_id'],
            'project_id': doc['project_id'],
            'document_name': doc['document_name'],
            'repair_reason': 'incomplete_processing',
            'description': doc['issue']
        })
    
    # Add inconsistent success (marked successful but no chunks - just reprocess)
    for doc in repair_analysis['inconsistent_success']:
        candidates_for_reprocessing.append({
            'document_id': doc['document_id'],
            'project_id': doc['project_id'],
            'document_name': doc['document_name'],
            'repair_reason': 'inconsistent_success',
            'description': doc['issue']
        })
    
    return candidates_for_reprocessing

def print_repair_analysis(project_id=None):
    """
    Print a detailed analysis of repair candidates for user review.
    
    Args:
        project_id (str, optional): Filter by project ID
    """
    repair_analysis = analyze_repair_candidates(project_id)
    
    print("\n🔧 REPAIR MODE ANALYSIS")
    print("=" * 80)
    
    total_issues = sum(len(issues) for issues in repair_analysis.values())
    
    if total_issues == 0:
        print("✅ No inconsistent document states found. Database is in good condition.")
        return
    
    print(f"Found {total_issues} documents with inconsistent states:")
    print()
    
    # Print each category
    for category, documents in repair_analysis.items():
        if not documents:
            continue
            
        category_names = {
            'partial_failures': '📄 Partial Processing Failures',
            'incomplete_processing': '⏸️  Incomplete Processing',
            'orphaned_chunks': '🗑️  Orphaned Chunks', 
            'missing_document_records': '📋 Missing Document Records',
            'inconsistent_success': '❌ Inconsistent Success Status'
        }
        
        print(f"{category_names.get(category, category)}: {len(documents)} documents")
        
        for doc in documents[:5]:  # Show first 5 as examples
            doc_name = doc.get('document_name', 'Unknown')[:60]
            print(f"  • {doc['document_id'][:12]}... - {doc_name}")
            print(f"    {doc['issue']}")
        
        if len(documents) > 5:
            print(f"  ... and {len(documents) - 5} more documents")
        print()
    
    # Count documents that will be reprocessed
    reprocess_candidates = get_repair_candidates_for_processing(project_id)
    print(f"🔄 Will clean up and reprocess: {len(reprocess_candidates)} documents")
    print("=" * 80)
