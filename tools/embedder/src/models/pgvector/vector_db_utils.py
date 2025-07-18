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
        # Start with large dataset parameters since you're planning to scale quickly
        print("Initializing HNSW indexes for large-scale continuous ingestion...")
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);
            """)
        )
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS ix_documents_embedding_vector
            ON documents USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);
            """)
        )
        
        # All the metadata indexes (these are always beneficial)
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_documents_metadata_type_id 
            ON documents ((document_metadata->>'document_type_id'));
            """)
        )
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_documents_metadata_date 
            ON documents ((document_metadata->>'document_date')) 
            WHERE document_metadata->>'document_date' IS NOT NULL;
            """)
        )
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_documents_metadata_status 
            ON documents ((document_metadata->>'document_status'));
            """)
        )
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_document_chunks_project_document 
            ON document_chunks (project_id, document_id);
            """)
        )
        
        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_documents_published_project 
            ON documents (project_id) 
            WHERE document_metadata->>'document_status' = 'published';
            """)
        )
        
        # Set runtime parameters for large datasets
        conn.execute(text("SET hnsw.ef_search = 200;"))
             
        conn.commit()
        print("HNSW indexes initialized for large-scale operations")

    # Add all GIN and regular indexes for metadata, tags, keywords, headings, project_id, etc.
    with engine.connect() as conn:
        print("Initializing all vector and metadata indexes...")
        # DocumentChunk indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_project_id ON document_chunks (project_id);
        """))
        # Document indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_documents_tags ON documents USING gin (document_tags);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_documents_keywords ON documents USING gin (document_keywords);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_documents_headings ON documents USING gin (document_headings);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_documents_metadata ON documents USING gin (document_metadata);
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_documents_project_id ON documents (project_id);
        """))
        # Project indexes
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_projects_metadata ON projects USING gin (project_metadata);
        """))
        # ProcessingLog: no custom indexes needed
        conn.commit()
        print("All vector and metadata indexes initialized")

def create_index(conn, sql, index_name):
    print(f"Creating index: {index_name} ...")
    conn.execute(text(sql))
    conn.commit()
    print(f"Index {index_name} created.")

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
        # Start with large dataset parameters since you're planning to scale quickly
        print("Initializing HNSW indexes for large-scale continuous ingestion...")
        
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);""",
            "ix_document_chunks_embedding_vector"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_embedding_vector
            ON documents USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);""",
            "ix_documents_embedding_vector"
        )
        
        # All the metadata indexes (these are always beneficial)
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS idx_documents_metadata_type_id 
            ON documents ((document_metadata->>'document_type_id'));""",
            "idx_documents_metadata_type_id"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS idx_documents_metadata_date 
            ON documents ((document_metadata->>'document_date')) 
            WHERE document_metadata->>'document_date' IS NOT NULL;""",
            "idx_documents_metadata_date"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS idx_documents_metadata_status 
            ON documents ((document_metadata->>'document_status'));""",
            "idx_documents_metadata_status"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS idx_document_chunks_project_document 
            ON document_chunks (project_id, document_id);""",
            "idx_document_chunks_project_document"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS idx_documents_published_project 
            ON documents (project_id) 
            WHERE document_metadata->>'document_status' = 'published';""",
            "idx_documents_published_project"
        )
        # Set runtime parameters for large datasets
        conn.execute(text("SET hnsw.ef_search = 200;"))
        conn.commit()
        print("HNSW indexes initialized for large-scale operations")

        # All GIN and regular indexes for metadata, tags, keywords, headings, project_id, etc.
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_document_chunks_project_id ON document_chunks (project_id);""",
            "ix_document_chunks_project_id"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_tags ON documents USING gin (document_tags);""",
            "ix_documents_tags"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_keywords ON documents USING gin (document_keywords);""",
            "ix_documents_keywords"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_headings ON documents USING gin (document_headings);""",
            "ix_documents_headings"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_metadata ON documents USING gin (document_metadata);""",
            "ix_documents_metadata"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_project_id ON documents (project_id);""",
            "ix_documents_project_id"
        )
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_projects_metadata ON projects USING gin (project_metadata);""",
            "ix_projects_metadata"
        )
        # ProcessingLog: no custom indexes needed
        print("All vector and metadata indexes initialized")

def get_session():
    """
    Create and return a new SQLAlchemy database session.
    
    This function provides a way to get a database session for interacting
    with the processing logs database using SQLAlchemy ORM.
    
    Returns:
        sqlalchemy.orm.Session: A new SQLAlchemy database session
    """
    return SessionLocal()