import os
import sys
import json
import time
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

# Add the parent directory to the Python path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings
from src.services.api_utils import get_files_for_project, get_projects, get_projects_count

"""
Script to retrospectively update metadata in chunks and tags tables with S3 keys.

This script:
1. Fetches all projects and their documents from the API
2. Creates a mapping of document_id to s3_key
3. Updates metadata in both chunks and tags tables in batches
4. Keeps track of progress and can be resumed if interrupted

Usage:
    python update_metadata_s3keys.py [--batch-size 1000] [--resume-from-project project_id]
"""

settings = get_settings()

def get_db_connection():
    """Create a database connection to the vector store."""
    return psycopg.connect(
        settings.vector_store_settings.db_url,
        row_factory=dict_row
    )

def get_all_document_s3_keys():
    """
    Fetch all documents from all projects and create a mapping of document_id to s3_key.
    
    Returns:
        dict: Mapping of document_id to s3_key
    """
    doc_mapping = {}
    
    # Get total number of projects
    projects_count = get_projects_count()
    page_size = 25
    total_pages = (projects_count + page_size - 1) // page_size

    print(f"Found {projects_count} total projects to process")
    
    for page_number in range(total_pages):
        projects = get_projects(page_number, page_size)
        
        for project in projects:
            project_id = project["_id"]
            project_name = project["name"]
            print(f"\nProcessing project: {project_name} ({project_id})")
            
            # Get all files for this project
            files_per_page = 50
            current_page = 0
            
            while True:
                files = get_files_for_project(project_id, current_page, files_per_page)
                if not files:
                    break
                
                for doc in files:
                    doc_id = doc["_id"]
                    s3_key = doc.get("internalURL")
                    if s3_key:
                        doc_mapping[doc_id] = s3_key
                
                current_page += 1
    
    print(f"\nCollected {len(doc_mapping)} document mappings")
    return doc_mapping

def update_table_metadata(conn, table_name, doc_mapping, batch_size=1000):
    """
    Update metadata in the specified table with S3 keys.
    
    Args:
        conn: Database connection
        table_name (str): Name of the table to update
        doc_mapping (dict): Mapping of document_id to s3_key
        batch_size (int): Number of records to update in each batch
    """
    print(f"\nProcessing table: {table_name}")
    
    with conn.cursor() as cur:
        # Get total count
        cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total_records = cur.fetchone()['count']
        print(f"Total records to process: {total_records}")
        
        # Process in batches
        offset = 0
        updated_count = 0
        error_count = 0
        
        while True:
            # Fetch batch of records
            cur.execute(f"""
                SELECT id, metadata
                FROM {table_name}
                WHERE 
                    metadata->>'document_id' IS NOT NULL
                    AND metadata->>'s3_key' IS NULL
                ORDER BY id
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            
            records = cur.fetchall()
            if not records:
                break
            
            # Process each record in the batch
            for record in records:
                try:
                    metadata = record['metadata']
                    doc_id = metadata.get('document_id')
                    
                    if doc_id in doc_mapping:
                        # Update metadata with s3_key
                        metadata['s3_key'] = doc_mapping[doc_id]
                        
                        cur.execute(f"""
                            UPDATE {table_name}
                            SET metadata = %s::jsonb
                            WHERE id = %s
                        """, (json.dumps(metadata), record['id']))
                        
                        updated_count += 1
                    else:
                        print(f"Warning: No S3 key found for document_id: {doc_id}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"Error updating record {record['id']}: {str(e)}")
                    error_count += 1
            
            # Commit the batch
            conn.commit()
            
            # Print progress
            progress = (offset + len(records)) / total_records * 100
            print(f"Progress: {progress:.2f}% - Updated: {updated_count}, Errors: {error_count}")
            
            offset += batch_size
    
    return updated_count, error_count

def main():
    start_time = datetime.now()
    print(f"Starting metadata update at {start_time}")
    
    try:
        # Get mapping of document_id to s3_key
        doc_mapping = get_all_document_s3_keys()
        
        # Create database connection
        conn = get_db_connection()
        
        try:
            # Update both tables
            for table in [
                settings.vector_store_settings.doc_chunks_name,
                settings.vector_store_settings.doc_tags_name
            ]:
                table_start = datetime.now()
                updated, errors = update_table_metadata(conn, table, doc_mapping)
                table_duration = datetime.now() - table_start
                
                print(f"\nTable {table} completed in {table_duration}")
                print(f"Records updated: {updated}")
                print(f"Errors encountered: {errors}")
        
        finally:
            conn.close()
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    duration = datetime.now() - start_time
    print(f"\nScript completed in {duration}")

if __name__ == "__main__":
    main()
