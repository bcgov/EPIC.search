from src.models import get_session
from src.models.pgvector.vector_models import ProcessingLog, DocumentChunk, Document
from sqlalchemy import text

"""
Repair Service module for identifying and fixing inconsistent document states.

This module provides functionality to detect and repair documents that are in 
inconsistent states due to interrupted processing, partial failures, or other issues.
"""

def bulk_cleanup_failed_documents(project_ids=None):
    """
    Bulk cleanup of ALL failed documents upfront, before processing starts.
    
    This removes chunks and document records for all failed documents in one
    sequential operation, avoiding concurrency issues during processing.
    
    Args:
        project_ids (list, optional): List of project IDs to clean up. If None, cleans all projects.
        
    Returns:
        dict: Summary of cleanup operations
    """
    import os
    from src.config.settings import get_settings
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import OperationalError
    import time
    
    settings = get_settings()
    process_id = os.getpid()
    
    # Use main database connection for bulk operations
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    
    # Single connection for bulk cleanup
    engine = create_engine(
        database_url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=60,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": "30",
            "application_name": f"epic_bulk_cleanup_{process_id}",
        }
    )
    
    @event.listens_for(engine, "connect")
    def set_bulk_timeouts(dbapi_connection, connection_record):
        """Set longer timeouts for bulk operations."""
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '600s'")  # 10 minutes for bulk ops
            cursor.execute("SET lock_timeout = '120s'")       # 2 minute lock timeout
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("BULK CLEANUP: Starting cleanup of all failed documents...")
        
        # Build project filter
        project_filter = ""
        if project_ids:
            project_list = "', '".join(project_ids)
            project_filter = f"AND pl.project_id IN ('{project_list}')"
        
        # Get all failed document IDs
        failed_docs_query = text(f"""
            SELECT DISTINCT pl.document_id, pl.project_id, 
                   pl.metrics->'document_info'->>'document_name' as doc_name,
                   pl.document_id as s3_key
            FROM processing_logs pl 
            WHERE pl.status = 'failure' {project_filter}
            ORDER BY pl.project_id, pl.document_id
        """)
        
        failed_docs = session.execute(failed_docs_query).fetchall()
        
        if not failed_docs:
            print("No failed documents found to clean up.")
            return {'documents_cleaned': 0, 'chunks_deleted': 0, 'document_records_deleted': 0, 'processing_logs_deleted': 0}
        
        print(f"Found {len(failed_docs)} failed documents to clean up")
        
        cleanup_summary = {
            'documents_cleaned': 0,
            'chunks_deleted': 0,
            'document_records_deleted': 0,
            'processing_logs_deleted': 0,  # Add this field to track log deletions
            'projects_affected': set(),
            'cleaned_files': []  # Track the actual files that were cleaned
        }
        
        # Process in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(failed_docs), batch_size):
            batch = failed_docs[i:i + batch_size]
            
            print(f"Cleaning batch {i//batch_size + 1}/{(len(failed_docs) + batch_size - 1)//batch_size} ({len(batch)} documents)...")
            
            # Extract document IDs for this batch
            doc_ids = [doc.document_id for doc in batch]
            project_ids_batch = [doc.project_id for doc in batch]
            
            # Track the files we're cleaning up for the return value
            for doc in batch:
                cleanup_summary['cleaned_files'].append({
                    'project_id': doc.project_id,
                    'document_id': doc.document_id
                    # Note: s3_key will be retrieved from API during queueing
                })
                cleanup_summary['projects_affected'].add(doc.project_id)
            
            # Bulk delete chunks for this batch
            chunks_deleted = session.query(DocumentChunk).filter(
                DocumentChunk.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            # Bulk delete document records for this batch  
            docs_deleted = session.query(Document).filter(
                Document.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            # Bulk delete processing logs for this batch (THIS WAS MISSING!)
            logs_deleted = session.query(ProcessingLog).filter(
                ProcessingLog.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            
            cleanup_summary['documents_cleaned'] += len(batch)
            cleanup_summary['chunks_deleted'] += chunks_deleted
            cleanup_summary['document_records_deleted'] += docs_deleted
            cleanup_summary['processing_logs_deleted'] = cleanup_summary.get('processing_logs_deleted', 0) + logs_deleted
            cleanup_summary['projects_affected'].update(project_ids_batch)
            
            print(f"  Batch complete: {chunks_deleted} chunks, {docs_deleted} document records, {logs_deleted} processing logs deleted")
        
        # Convert set to count for final summary
        cleanup_summary['projects_affected'] = len(cleanup_summary['projects_affected'])
        
        print(f"BULK CLEANUP COMPLETE:")
        print(f"   Documents cleaned: {cleanup_summary['documents_cleaned']}")
        print(f"   Chunks deleted: {cleanup_summary['chunks_deleted']}")
        print(f"   Document records deleted: {cleanup_summary['document_records_deleted']}")
        print(f"   Processing logs deleted: {cleanup_summary['processing_logs_deleted']}")
        print(f"   Projects affected: {cleanup_summary['projects_affected']}")
        
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        print(f"Error during bulk cleanup: {e}")
        raise
    finally:
        try:
            session.close()
            engine.dispose()
        except:
            pass


def bulk_cleanup_skipped_documents(project_ids=None):
    """
    Bulk cleanup of ALL skipped documents upfront, before processing starts.
    
    This removes processing logs for all skipped documents in one
    sequential operation, allowing them to be reprocessed.
    
    Args:
        project_ids (list, optional): List of project IDs to clean up. If None, cleans all projects.
        
    Returns:
        dict: Summary of cleanup operations
    """
    import os
    from src.config.settings import get_settings
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import OperationalError
    import time
    
    settings = get_settings()
    process_id = os.getpid()
    
    # Use main database connection for bulk operations
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    
    # Single connection for bulk cleanup
    engine = create_engine(
        database_url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=60,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": "30",
        }
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    try:
        print("BULK CLEANUP: Starting cleanup of all skipped documents...")
        
        # Build project filter
        project_filter = ""
        if project_ids:
            project_ids_str = "', '".join(project_ids)
            project_filter = f"AND pl.project_id IN ('{project_ids_str}')"
        
        # Get all skipped document IDs
        skipped_docs_query = text(f"""
            SELECT DISTINCT pl.document_id, pl.project_id, 
                   pl.metrics->'document_info'->>'document_name' as doc_name
            FROM processing_logs pl 
            WHERE pl.status = 'skipped' {project_filter}
            ORDER BY pl.project_id, pl.document_id
        """)
        
        skipped_docs = session.execute(skipped_docs_query).fetchall()
        
        if not skipped_docs:
            print("No skipped documents found to clean up.")
            return {'documents_cleaned': 0, 'processing_logs_deleted': 0}
        
        print(f"Found {len(skipped_docs)} skipped documents to clean up")
        
        cleanup_summary = {
            'documents_cleaned': 0,
            'processing_logs_deleted': 0,
            'projects_affected': set(),
            'cleaned_files': []
        }
        
        # Process in batches to avoid overwhelming the database
        batch_size = 100
        for i in range(0, len(skipped_docs), batch_size):
            batch = skipped_docs[i:i + batch_size]
            
            print(f"Cleaning batch {i//batch_size + 1}/{(len(skipped_docs) + batch_size - 1)//batch_size} ({len(batch)} documents)...")
            
            doc_ids = [doc.document_id for doc in batch]
            project_ids_batch = [doc.project_id for doc in batch]
            
            # Track the files we're cleaning up for the return value
            for doc in batch:
                cleanup_summary['cleaned_files'].append({
                    'project_id': doc.project_id,
                    'document_id': doc.document_id
                    # Note: s3_key will be retrieved from API during queueing
                })
                cleanup_summary['projects_affected'].add(doc.project_id)
            
            # Delete processing logs only (no chunks or document records for skipped files)
            logs_deleted = session.query(ProcessingLog).filter(
                ProcessingLog.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            
            cleanup_summary['documents_cleaned'] += len(batch)
            cleanup_summary['processing_logs_deleted'] += logs_deleted
            
            print(f"  Batch complete: {logs_deleted} processing logs deleted")
        
        cleanup_summary['projects_affected'] = len(cleanup_summary['projects_affected'])
        
        print(f"BULK CLEANUP COMPLETE:")
        print(f"   Documents cleaned: {cleanup_summary['documents_cleaned']}")
        print(f"   Processing logs deleted: {cleanup_summary['processing_logs_deleted']}")
        print(f"   Projects affected: {cleanup_summary['projects_affected']}")
        
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        print(f"Error during bulk cleanup: {e}")
        raise
    finally:
        try:
            session.close()
            engine.dispose()
        except:
            pass


def bulk_cleanup_repair_candidates(project_ids=None):
    """
    Bulk cleanup of repair candidates (documents with inconsistent states) upfront.
    
    This identifies and cleans up documents that are in inconsistent states due to
    interrupted processing, partial failures, or other issues.
    
    Args:
        project_ids (list, optional): List of project IDs to clean up. If None, cleans all projects.
        
    Returns:
        dict: Summary of cleanup operations
    """
    print("REPAIR MODE: Analyzing database for inconsistent document states...")
    
    # Get repair candidates that need cleanup and reprocessing
    repair_candidates = get_repair_candidates_for_processing(project_ids[0] if project_ids else None)
    
    if not repair_candidates:
        print("No repair candidates found. Database is in good condition.")
        return {'documents_cleaned': 0, 'chunks_deleted': 0, 'document_records_deleted': 0}
    
    print(f"Found {len(repair_candidates)} documents needing repair:")
    for candidate in repair_candidates[:5]:  # Show first 5
        print(f"  • {candidate['document_id'][:12]}... - {candidate['repair_reason']}")
    if len(repair_candidates) > 5:
        print(f"  ... and {len(repair_candidates) - 5} more documents")
    
    # Now perform bulk cleanup of these candidates
    import os
    from src.config.settings import get_settings
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    
    settings = get_settings()
    process_id = os.getpid()
    
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    
    engine = create_engine(
        database_url,
        pool_size=1,
        max_overflow=0,
        pool_timeout=60,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": "30",
            "application_name": f"epic_repair_cleanup_{process_id}",
        }
    )
    
    @event.listens_for(engine, "connect")
    def set_bulk_timeouts(dbapi_connection, connection_record):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '600s'")
            cursor.execute("SET lock_timeout = '120s'")
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        cleanup_summary = {
            'documents_cleaned': 0,
            'chunks_deleted': 0,
            'document_records_deleted': 0,
            'processing_logs_deleted': 0,
            'projects_affected': set(),
            'cleaned_files': []  # Track the actual files that were cleaned
        }
        
        # Process in batches
        batch_size = 100
        for i in range(0, len(repair_candidates), batch_size):
            batch = repair_candidates[i:i + batch_size]
            
            print(f"Cleaning repair batch {i//batch_size + 1}/{(len(repair_candidates) + batch_size - 1)//batch_size} ({len(batch)} documents)...")
            
            doc_ids = [candidate['document_id'] for candidate in batch]
            project_ids_batch = [candidate['project_id'] for candidate in batch]
            
            # Track the files we're cleaning up for the return value
            for candidate in batch:
                cleanup_summary['cleaned_files'].append({
                    'project_id': candidate['project_id'],
                    'document_id': candidate['document_id']
                    # Note: s3_key will be retrieved from API during queueing
                })
            
            # Delete chunks
            chunks_deleted = session.query(DocumentChunk).filter(
                DocumentChunk.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            # Delete document records
            docs_deleted = session.query(Document).filter(
                Document.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            # For repair mode, also delete processing logs to start fresh
            logs_deleted = session.query(ProcessingLog).filter(
                ProcessingLog.document_id.in_(doc_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            
            cleanup_summary['documents_cleaned'] += len(batch)
            cleanup_summary['chunks_deleted'] += chunks_deleted
            cleanup_summary['document_records_deleted'] += docs_deleted
            cleanup_summary['processing_logs_deleted'] += logs_deleted
            cleanup_summary['projects_affected'].update(project_ids_batch)
            
            print(f"  Repair batch complete: {chunks_deleted} chunks, {docs_deleted} docs, {logs_deleted} logs deleted")
        
        cleanup_summary['projects_affected'] = len(cleanup_summary['projects_affected'])
        
        print(f"REPAIR CLEANUP COMPLETE:")
        print(f"   Documents cleaned: {cleanup_summary['documents_cleaned']}")
        print(f"   Chunks deleted: {cleanup_summary['chunks_deleted']}")
        print(f"   Document records deleted: {cleanup_summary['document_records_deleted']}")
        print(f"   Processing logs deleted: {cleanup_summary['processing_logs_deleted']}")
        print(f"   Projects affected: {cleanup_summary['projects_affected']}")
        
        return cleanup_summary
        
    except Exception as e:
        session.rollback()
        print(f"Error during repair cleanup: {e}")
        raise
    finally:
        try:
            session.close()
            engine.dispose()
        except:
            pass

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
    
    Uses a worker-specific database engine to avoid SSL connection issues.
    
    Args:
        document_id (str): The document ID to clean up
        project_id (str): The project ID the document belongs to
        
    Returns:
        dict: Summary of what was cleaned up
    """
    import os
    from src.config.settings import get_settings
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import OperationalError
    import time
    
    settings = get_settings()
    process_id = os.getpid()
    
    # Worker-specific database settings for cleanup operations
    WORKER_POOL_SIZE = int(os.getenv('WORKER_POOL_SIZE', '1'))
    WORKER_MAX_OVERFLOW = int(os.getenv('WORKER_MAX_OVERFLOW', '2'))
    WORKER_POOL_TIMEOUT = int(os.getenv('WORKER_POOL_TIMEOUT', '30'))
    WORKER_CONNECT_TIMEOUT = int(os.getenv('WORKER_CONNECT_TIMEOUT', '30'))
    
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    
    # Create process-specific engine for cleanup
    engine_to_use = create_engine(
        database_url,
        pool_size=WORKER_POOL_SIZE,
        max_overflow=WORKER_MAX_OVERFLOW,
        pool_timeout=WORKER_POOL_TIMEOUT,
        pool_recycle=1800,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": WORKER_CONNECT_TIMEOUT,
            "application_name": f"epic_embedder_cleanup_full_{process_id}",
            "prepare_threshold": None
        }
    )
    
    @event.listens_for(engine_to_use, "connect")
    def set_cleanup_timeouts(dbapi_connection, connection_record):
        """Set statement and lock timeouts for cleanup connections."""
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '300s'")
            cursor.execute("SET lock_timeout = '60s'")
    
    Session = sessionmaker(bind=engine_to_use)
    session = Session()
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            cleanup_summary = {
                'chunks_deleted': 0,
                'document_records_deleted': 0,
                'processing_logs_deleted': 0
            }
            
            print(f"[CLEANUP] Attempt {attempt + 1}/{max_retries}: Full cleanup of document {document_id}...")
            
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
            print(f"[CLEANUP] Successfully completed full cleanup: {cleanup_summary}")
            return cleanup_summary
            
        except OperationalError as e:
            session.rollback()
            if "SSL error" in str(e) or "EOF detected" in str(e) or "consuming input failed" in str(e):
                print(f"[CLEANUP] SSL/Connection error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"[CLEANUP] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                    try:
                        session.close()
                    except:
                        pass
                    session = Session()
                    continue
                else:
                    print(f"[CLEANUP] Failed full cleanup after {max_retries} attempts due to connection issues")
                    raise
            else:
                print(f"[CLEANUP] Non-connection error: {e}")
                raise
        except Exception as e:
            session.rollback()
            print(f"[CLEANUP] Unexpected error during full cleanup: {e}")
            raise
        finally:
            try:
                session.close()
            except:
                pass


def cleanup_document_content_for_retry(document_id: str, project_id: str):
    """
    Clean up document content (chunks and records) for retry processing.
    
    This removes chunks and document records but preserves processing logs
    so that the retry status is maintained until successful reprocessing.
    
    Uses a worker-specific database engine to avoid SSL connection issues.
    
    Args:
        document_id (str): The document ID to clean up
        project_id (str): The project ID the document belongs to
        
    Returns:
        dict: Summary of what was cleaned up
    """
    import os
    from src.config.settings import get_settings
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import OperationalError
    import time
    
    settings = get_settings()
    process_id = os.getpid()
    
    # Worker-specific database settings for cleanup operations
    WORKER_POOL_SIZE = int(os.getenv('WORKER_POOL_SIZE', '1'))
    WORKER_MAX_OVERFLOW = int(os.getenv('WORKER_MAX_OVERFLOW', '2'))
    WORKER_POOL_TIMEOUT = int(os.getenv('WORKER_POOL_TIMEOUT', '30'))
    WORKER_CONNECT_TIMEOUT = int(os.getenv('WORKER_CONNECT_TIMEOUT', '30'))
    
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    
    # Create process-specific engine with worker settings for cleanup
    engine_to_use = create_engine(
        database_url,
        pool_size=WORKER_POOL_SIZE,
        max_overflow=WORKER_MAX_OVERFLOW,
        pool_timeout=WORKER_POOL_TIMEOUT,
        pool_recycle=1800,     # 30 minutes
        pool_pre_ping=True,    # Verify connections before use
        connect_args={
            "sslmode": "prefer",
            "connect_timeout": WORKER_CONNECT_TIMEOUT,
            "application_name": f"epic_embedder_cleanup_{process_id}",
            "prepare_threshold": None   # Disable prepared statements to avoid P03 errors
        }
    )
    
    # Set timeouts after connection establishment for cleanup worker's engine
    @event.listens_for(engine_to_use, "connect")
    def set_cleanup_timeouts(dbapi_connection, connection_record):
        """Set statement and lock timeouts for cleanup connections."""
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET statement_timeout = '300s'")  # 5 minute query timeout
            cursor.execute("SET lock_timeout = '60s'")        # 1 minute lock timeout
    
    Session = sessionmaker(bind=engine_to_use)
    session = Session()
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            cleanup_summary = {
                'chunks_deleted': 0,
                'document_records_deleted': 0,
                'processing_logs_preserved': 0
            }
            
            print(f"[CLEANUP] Attempt {attempt + 1}/{max_retries}: Cleaning up document {document_id} for retry...")
            
            # Delete chunks with retry logic
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
            print(f"[CLEANUP] Successfully cleaned up: {cleanup_summary}")
            return cleanup_summary
            
        except OperationalError as e:
            session.rollback()
            if "SSL error" in str(e) or "EOF detected" in str(e) or "consuming input failed" in str(e):
                print(f"[CLEANUP] SSL/Connection error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    print(f"[CLEANUP] Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                    # Close and recreate session for next attempt
                    try:
                        session.close()
                    except:
                        pass
                    session = Session()
                    continue
                else:
                    print(f"[CLEANUP] Failed cleanup after {max_retries} attempts due to connection issues")
                    raise
            else:
                # Non-connection error, re-raise immediately
                print(f"[CLEANUP] Non-connection error: {e}")
                raise
        except Exception as e:
            session.rollback()
            print(f"[CLEANUP] Unexpected error during cleanup: {e}")
            raise
        finally:
            try:
                session.close()
            except:
                pass


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
    
    print("\nREPAIR MODE ANALYSIS")
    print("=" * 80)
    
    total_issues = sum(len(issues) for issues in repair_analysis.values())
    
    if total_issues == 0:
        print("No inconsistent document states found. Database is in good condition.")
        return
    
    print(f"Found {total_issues} documents with inconsistent states:")
    print()
    
    # Print each category
    for category, documents in repair_analysis.items():
        if not documents:
            continue
            
        category_names = {
            'partial_failures': 'Partial Processing Failures',
            'incomplete_processing': 'Incomplete Processing',
            'orphaned_chunks': 'Orphaned Chunks', 
            'missing_document_records': 'Missing Document Records',
            'inconsistent_success': 'Inconsistent Success Status'
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
    print(f"Will clean up and reprocess: {len(reprocess_candidates)} documents")
    print("=" * 80)
