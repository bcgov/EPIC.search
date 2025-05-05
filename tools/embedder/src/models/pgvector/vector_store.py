import psycopg
from psycopg.rows import dict_row
import json
from typing import List, Optional
from src.config import get_settings
import numpy as np

"""
Vector Store module for PostgreSQL with pgvector extension.

This module provides a VectorStore class that handles interactions with a PostgreSQL
database using the pgvector extension. It enables the storage, indexing, and search of
vector embeddings along with their associated metadata and content.
"""

class VectorStore:
    """
    PostgreSQL vector database client using pgvector extension.
    
    This class manages connections to a PostgreSQL database with pgvector extension
    and provides methods for creating tables, inserting records with vector embeddings,
    and searching for similar vectors using cosine similarity.
    
    Attributes:
        settings: Configuration settings for the vector database connection
        _connections (dict): Dictionary of database connections for different tables
    """
    def __init__(self):
        """
        Initialize the VectorStore with settings from the application configuration.
        
        Sets up the connection settings but doesn't establish database connections
        until they are needed, following a lazy initialization pattern.
        """
        self.settings = get_settings().vector_store_settings    
        self._connections = {}

    def get_connection_for_table(self, table_name: str):
        """
        Get or create a database connection for the specified table.
        
        Args:
            table_name (str): Name of the table to connect to
            
        Returns:
            psycopg.Connection: A PostgreSQL database connection
        """
        if table_name not in self._connections:
            conn = psycopg.connect(
                self.settings.db_url,
                row_factory=dict_row
            )
            self._connections[table_name] = conn
        return self._connections[table_name]

    def create_table(self, table_name: str, embedding_dimensions: Optional[int] = None) -> None:
        """
        Create a new table with vector support.
        
        Creates a table with columns for ID, vector embedding, JSON metadata,
        text content, and creation timestamp.
        
        Args:
            table_name (str): Name of the table to create
            embedding_dimensions (int, optional): Dimensionality of the embedding vectors.
                                                If None, uses value from settings.
        """
        if embedding_dimensions is None:
            embedding_dimensions = int(self.settings.embedding_dimensions)
            
        conn = self.get_connection_for_table(table_name)
        with conn.cursor() as cur:
            # Ensure pgvector extension is available
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Create table with vector column
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    embedding vector({embedding_dimensions}),
                    metadata JSONB,
                    content TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()

    def create_index(self, table_name: str) -> None:
        """
        Create a vector index on the table for faster similarity searches.
        
        Creates an HNSW (Hierarchical Navigable Small World) index on the embedding
        column, which is optimized for approximate nearest neighbor search.
        
        Args:
            table_name (str): Name of the table to index
        """
        conn = self.get_connection_for_table(table_name)
        with conn.cursor() as cur:
            # Create an HNSW index for faster vector search
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_embedding 
                ON {table_name} 
                USING hnsw (embedding vector_cosine_ops)
            """)
        conn.commit()

    def drop_index(self, table_name: str) -> None:
        """
        Drop the vector index from the table.
        
        This can be useful when rebuilding indexes or when the index is no longer needed.
        
        Args:
            table_name (str): Name of the table to remove the index from
        """
        conn = self.get_connection_for_table(table_name)
        with conn.cursor() as cur:
            cur.execute(f"""
                DROP INDEX IF EXISTS idx_{table_name}_embedding
            """)
        conn.commit()
    
    def insert(self, table_name: str, records: List) -> None:
        """
        Insert records with vector embeddings into the table.
        
        This method supports different record formats:
        1. Dictionaries with 'embedding', 'metadata', and 'content' keys
        2. Tuples with embedding, metadata, and content elements
        3. Objects with page_content and metadata attributes (like LangChain documents)
        
        Args:
            table_name (str): Name of the table to insert records into
            records (List): List of records to insert
        """
        if not records:
            return
            
        conn = self.get_connection_for_table(table_name)
        
        with conn.cursor() as cur:
            for record in records:
                try:
                    # Extract data based on record type
                    if isinstance(record, dict):
                        embedding = record.get('embedding')
                        metadata = record.get('metadata', {})
                        content = record.get('content', '')
                    elif isinstance(record, tuple) and len(record) >= 3:
                        embedding, metadata, content = record[0], record[1], record[2]
                    elif hasattr(record, 'page_content') and hasattr(record, 'metadata'):
                        content = record.page_content
                        metadata = record.metadata
                        embedding = getattr(record, 'embedding', None)
                    else:
                        print(f"Skipping record of unsupported type: {type(record)}")
                        continue
                        
                    # Make sure metadata is a dict
                    if metadata is None:
                        metadata = {}
                    
                    # Skip records with no embedding
                    if embedding is None:
                        print(f"Skipping record with no embedding")
                        continue
                    
                    # Convert NumPy ndarray to list (THIS IS THE KEY FIX)
                    if isinstance(embedding, np.ndarray):
                        embedding = embedding.tolist()
                    
                    # Skip string embeddings
                    if isinstance(embedding, str):
                        print(f"Skipping record with invalid embedding format (string): {embedding[:30]}...")
                        continue
                    
                    # Check embedding format
                    if not isinstance(embedding, (list, tuple)):
                        print(f"Skipping record with invalid embedding type: {type(embedding)}")
                        continue
                    
                    # Insert the record
                    cur.execute(f"""
                        INSERT INTO {table_name} (embedding, metadata, content)
                        VALUES (%s::vector, %s, %s)
                    """, (embedding, json.dumps(metadata), content))
                    
                except Exception as e:
                    print(f"Error inserting record: {str(e)}")
                    continue
                    
        conn.commit()

    def delete_by_metadata(self, table_name: str, metadata_filters: dict) -> None:
        """
        Delete records that match specific metadata filters.
        
        This allows for selective deletion of records based on their metadata values.
        
        Args:
            table_name (str): Name of the table to delete records from
            metadata_filters (dict): Dictionary of metadata key-value pairs to match
        """
        if not metadata_filters:
            return
            
        conn = self.get_connection_for_table(table_name)
        with conn.cursor() as cur:
            conditions = []
            params = []
            for key, value in metadata_filters.items():
                conditions.append(f"metadata->>'%s' = %s")
                params.extend([key, value])
            
            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            
            cur.execute(query, params)
        conn.commit()
        
    def search(self, table_name: str, query_embedding: List[float], limit: int = 10) -> List[dict]:
        """
        Search for similar vectors in the database using cosine similarity.
        
        This method uses the pgvector <=> operator, which computes cosine distance.
        The results are returned in order of decreasing similarity.
        
        Args:
            table_name (str): Name of the table to search in
            query_embedding (List[float]): Vector embedding to search for
            limit (int, optional): Maximum number of results to return. Defaults to 10.
            
        Returns:
            List[dict]: List of dictionaries containing the search results with similarity scores
        """
        conn = self.get_connection_for_table(table_name)
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, metadata, content, 1 - (embedding <=> %s::vector) as similarity
                FROM {table_name}
                ORDER BY similarity DESC
                LIMIT %s
            """, (query_embedding, limit))
            return cur.fetchall()
            
    def __del__(self):
        """
        Close all database connections when the VectorStore object is destroyed.
        
        This ensures proper cleanup of resources when the object is garbage collected.
        """
        for conn in self._connections.values():
            conn.close()