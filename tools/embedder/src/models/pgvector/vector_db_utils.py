from .vector_store import VectorStore

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

"""
Vector Database Utilities module for pgvector integration.

This module provides utility functions for initializing and managing the
PostgreSQL vector database using the pgvector extension. It handles table creation,
index creation, and database setup required for vector similarity search.
"""

from src.config.settings import get_settings
settings = get_settings()


def init_vec_db():
    """
    Initialize the vector database tables and indexes.
    
    This function creates the necessary tables and vector indexes for storing 
    document chunks and their vector embeddings. It creates:
    
    1. An index table for storing document tags with their embeddings
    2. A chunk table for storing document chunks with their embeddings
    3. Vector indexes for efficient similarity search on both tables
    
    This should be called when the application starts to ensure the vector
    database is properly set up.
    
    Returns:
        None
    """
    vec = VectorStore()
    
    # Create tables
    vec.create_table(settings.vector_store_settings.doc_tags_name)
    vec.create_table(settings.vector_store_settings.doc_chunks_name)
    
    # Create vector indexes for better performance
    vec.create_index(settings.vector_store_settings.doc_tags_name)
    vec.create_index(settings.vector_store_settings.doc_chunks_name)
