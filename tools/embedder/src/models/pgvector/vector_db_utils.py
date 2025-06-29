from .vector_store import VectorStore
from sqlalchemy.orm import sessionmaker

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

"""
Vector Database Utilities module for unified pgvector integration and ORM management.

- Handles table creation, dropping, and index setup for all vector and log tables
- Uses SQLAlchemy ORM for all schema operations
- Adds HNSW indexes for fast semantic search (via raw SQL)
- Controlled by a reset_db setting (default: False) for safe production use
- All models (chunks, documents, projects, logs) now share a single database and Base
"""

from src.config.settings import get_settings
from src.models.pgvector.vector_models import Base, DocumentChunk, Document, Project, ProcessingLog
from sqlalchemy import create_engine, text

settings = get_settings()

# Use SQLAlchemy to drop and create tables    
database_url = settings.vector_store_settings.db_url
# Set up SQLAlchemy session    
if database_url and database_url.startswith('postgresql:'):
    database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)
    
def init_vec_db():
    """
    Initialize all vector and log database tables and indexes using SQLAlchemy ORM.
    Drops and recreates tables only if reset_db is True (dev/test only!).
    Ensures pgvector extension and HNSW indexes are present for semantic search.
    """
    vec = VectorStore()
    # Initialize the pgvector extension (raw SQL, required for embedding column)
    vec.create_pgvector_extension()

    # Only drop and recreate tables if setting is enabled (default: False)
    reset_db = getattr(settings.vector_store_settings, 'reset_db', False)
    if reset_db:
        # Drop all vector tables (dev/test only!)
        Base.metadata.drop_all(engine, tables=[DocumentChunk.__table__, Document.__table__, Project.__table__, ProcessingLog.__table__])
        # Create all vector tables and indexes
        Base.metadata.create_all(engine, tables=[DocumentChunk.__table__, Document.__table__, Project.__table__, ProcessingLog.__table__])

    # Add HNSW vector indexes with explicit operator class (required by pgvector)
    with engine.connect() as conn:
        # DocumentChunk embedding index
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
            ON document_chunks USING hnsw (embedding vector_cosine_ops);
            """)
        )
        # Document embedding index
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_documents_embedding_vector
            ON documents USING hnsw (embedding vector_cosine_ops);
            """)
        )
        conn.commit()

def get_session():
    """
    Create and return a new SQLAlchemy database session.
    
    This function provides a way to get a database session for interacting
    with the processing logs database using SQLAlchemy ORM.
    
    Returns:
        sqlalchemy.orm.Session: A new SQLAlchemy database session
    """
    return SessionLocal()