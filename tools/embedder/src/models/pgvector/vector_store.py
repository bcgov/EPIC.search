import psycopg

from psycopg.rows import dict_row
from typing import List
from src.config import get_settings
from src.config.settings import get_settings

settings = get_settings()
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

    def check_extension_exists(self, conn) -> bool:
        """
        Check if the pgvector extension is already installed in the database.
        
        Args:
            conn (psycopg.Connection): A PostgreSQL database connection
            
        Returns:
            bool: True if the extension exists, False otherwise
        """
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM pg_extension WHERE extname = 'vector'
            """)
            return bool(cur.fetchone())
            
    def create_pgvector_extension(self) -> bool:
        """
        Create the pgvector extension in the PostgreSQL database.
        
        This is required for vector operations and should be called once
        during database initialization. It can be configured through the
        AUTO_CREATE_PGVECTOR_EXTENSION environment variable.
        
        Returns:
            bool: True if the extension was created or already exists, False otherwise
        """
        # Get a connection without specifying a table
        conn = psycopg.connect(
            self.settings.db_url,
            row_factory=dict_row
        )
        
        try:
            # Always check if extension exists first
            exists = self.check_extension_exists(conn)
            if exists:
                return True
                
            # If extension doesn't exist, try to create it if auto_create is enabled
            auto_create_extension = getattr(settings.vector_store_settings, 'auto_create_extension', True)
            if auto_create_extension:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                conn.commit()
                return True
            else:
                # Extension doesn't exist and auto-create is disabled
                raise RuntimeError(
                    "The pgvector extension is not installed in the database and "
                    "auto_create_extension is set to False. Please install the extension "
                    "manually or set AUTO_CREATE_PGVECTOR_EXTENSION=True."
                )
        finally:
            conn.close()
        
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