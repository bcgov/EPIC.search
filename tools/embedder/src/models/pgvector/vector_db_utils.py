def ensure_primary_key(conn, table, pk_column):
    """
    Ensure the given table has a primary key on pk_column. Adds PK if missing.
    Only works if pk_column is unique and not null for all rows.
    """
    from sqlalchemy import text
    result = conn.execute(text(
        f"""SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE table_name = '{table}' AND constraint_type = 'PRIMARY KEY';"""
    ))
    if result.scalar() == 0:
        print(f"Adding primary key to {table} on column {pk_column}...")
        conn.execute(text(f'ALTER TABLE {table} ADD PRIMARY KEY ({pk_column});'))
        conn.commit()
    else:
        print(f"Primary key already exists for {table}.")
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

# Configure engine with connection pooling and timeout settings for server stability
engine = create_engine(
    database_url,
    pool_size=20,           # Increased for high-concurrency server
    max_overflow=40,        # Additional connections beyond pool_size for burst loads
    pool_timeout=60,        # Seconds to wait for connection from pool
    pool_recycle=1800,      # Recycle connections after 30 minutes
    pool_pre_ping=True,     # Verify connections before use
    connect_args={
        "sslmode": "prefer",  # Use SSL when available but don't require it
        "connect_timeout": 60,  # Connection timeout in seconds
        "application_name": "epic_embedder_server"  # Identify in database logs
    }
)
SessionLocal = sessionmaker(bind=engine)
    

def create_index(conn, sql, index_name):
    print(f"Creating index: {index_name} ...")
    conn.execute(text(sql))
    conn.commit()
    print(f"Index {index_name} created.")

def init_vec_db(skip_hnsw=False):
    """
    Initialize all vector and log database tables and indexes using SQLAlchemy ORM.
    Drops and recreates tables only if reset_db is True (dev/test only!).
    Ensures pgvector extension and all metadata indexes are present for semantic search.
    By default, also creates HNSW indexes unless skip_hnsw=True.
    """
    vec = VectorStore()
    # Initialize the pgvector extension (raw SQL, required for embedding column)
    vec.create_pgvector_extension()

    # Drop and recreate tables if reset_db is True (dev/test only!)
    if settings.vector_store_settings.reset_db:
        print("[WARNING] RESET_DB=True - Dropping all existing tables and data!")
        Base.metadata.drop_all(engine, tables=[DocumentChunk.__table__, Document.__table__, Project.__table__, ProcessingLog.__table__])
        print("[DB RESET] All tables dropped successfully.")

    # Create tables and PKs if missing (safe for production)
    Base.metadata.create_all(engine, tables=[DocumentChunk.__table__, Document.__table__, Project.__table__, ProcessingLog.__table__])

    # Add metadata, GIN, and regular indexes for metadata, tags, keywords, headings, project_id, etc.
    with engine.connect() as conn:
        print("Initializing all metadata and regular indexes...")
        # Ensure primary keys exist for all main tables
        ensure_primary_key(conn, 'document_chunks', 'id')
        ensure_primary_key(conn, 'documents', 'document_id')
        ensure_primary_key(conn, 'projects', 'project_id')
        ensure_primary_key(conn, 'processing_logs', 'id')
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
        conn.commit()
        print("All metadata and regular indexes initialized")

    # Add HNSW vector indexes unless skipped
    if not skip_hnsw:
        print("[DB INIT] Creating HNSW vector indexes (semantic search acceleration)...")
        create_hnsw_indexes()
    else:
        print("[DB INIT] Skipping HNSW vector index creation (--skip-hnsw-indexes flag is set or skip_hnsw=True)")

def create_hnsw_indexes():
    """
    Create HNSW vector indexes for semantic search. Can be skipped via flag in init_vec_db.
    """
    with engine.connect() as conn:
        print("[DB INIT] Starting HNSW index creation...")
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_vector
            ON document_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);""",
            "ix_document_chunks_embedding_vector"
        )
        print("[DB INIT] Created ix_document_chunks_embedding_vector.")
        create_index(conn,
            """CREATE INDEX IF NOT EXISTS ix_documents_embedding_vector
            ON documents USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 400);""",
            "ix_documents_embedding_vector"
        )
        print("[DB INIT] Created ix_documents_embedding_vector.")
        # Set runtime parameters for large datasets
        conn.execute(text("SET hnsw.ef_search = 200;"))
        conn.commit()
        print("[DB INIT] Finished HNSW index creation.")