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
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
import os
import multiprocessing

settings = get_settings()

def _parse_files_concurrency():
    """Parse FILES_CONCURRENCY_SIZE with intelligent auto-calculation (matches settings.py logic)"""
    env_value = os.environ.get("FILES_CONCURRENCY_SIZE", "")
    cpu_count = multiprocessing.cpu_count()
    
    # Handle empty or auto values with intelligent defaults
    if not env_value or env_value.lower() == 'auto':
        # For high-core systems, use half the cores to avoid over-parallelization
        if cpu_count >= 16:
            return cpu_count // 2
        else:
            return cpu_count
    elif env_value.lower() == 'auto-full':
        return cpu_count
    elif env_value.lower() == 'auto-conservative':
        return max(1, cpu_count // 4)
    
    try:
        # Try to parse as integer
        return int(env_value)
    except ValueError:
        # If parsing fails, fall back to intelligent auto
        return cpu_count // 2 if cpu_count >= 16 else cpu_count

def _calculate_auto_db_pool_config():
    """Calculate database pool settings based on concurrency"""
    concurrent_workers = _parse_files_concurrency()
    
    # Calculate pool sizes based on concurrent workers
    # Formula: pool_size = 2x workers (safe ratio), overflow = 4x workers (good capacity)
    auto_pool_size = max(4, concurrent_workers * 2)
    auto_max_overflow = max(8, concurrent_workers * 4)
    
    return auto_pool_size, auto_max_overflow, concurrent_workers

# Get auto-calculated values
auto_pool_size, auto_max_overflow, estimated_workers = _calculate_auto_db_pool_config()

# Configurable connection pool settings via environment variables with AUTO support
DB_POOL_SIZE_RAW = os.getenv('DB_POOL_SIZE', 'auto').lower()
DB_MAX_OVERFLOW_RAW = os.getenv('DB_MAX_OVERFLOW', 'auto').lower()

if DB_POOL_SIZE_RAW == 'auto':
    DB_POOL_SIZE = auto_pool_size
else:
    DB_POOL_SIZE = int(DB_POOL_SIZE_RAW)

if DB_MAX_OVERFLOW_RAW == 'auto':
    DB_MAX_OVERFLOW = auto_max_overflow
else:
    DB_MAX_OVERFLOW = int(DB_MAX_OVERFLOW_RAW)

DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '900'))      # Default: 15 minutes
DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '120'))      # Default: 2 minutes to wait for connection from pool
DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', '60')) # Default: 1 minute to establish initial connection

print(f"[CONFIG] Database connection pool: size={DB_POOL_SIZE}, max_overflow={DB_MAX_OVERFLOW}, "
      f"recycle={DB_POOL_RECYCLE}s ({DB_POOL_RECYCLE//60} min), "
      f"pool_timeout={DB_POOL_TIMEOUT}s, connect_timeout={DB_CONNECT_TIMEOUT}s")
if DB_POOL_SIZE_RAW == 'auto' or DB_MAX_OVERFLOW_RAW == 'auto':
    print(f"[CONFIG] Auto-calculated for ~{estimated_workers} concurrent workers "
          f"(FILES_CONCURRENCY_SIZE={os.getenv('FILES_CONCURRENCY_SIZE', 'auto')})")

# Use SQLAlchemy to drop and create tables    
database_url = settings.vector_store_settings.db_url
# Set up SQLAlchemy session    
if database_url and database_url.startswith('postgresql:'):
    database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')

# Configure engine with connection pooling and timeout settings for server
engine = create_engine(
    database_url,
    pool_size=DB_POOL_SIZE,         # Configurable via DB_POOL_SIZE env var
    max_overflow=DB_MAX_OVERFLOW,   # Configurable via DB_MAX_OVERFLOW env var
    pool_timeout=DB_POOL_TIMEOUT,   # Configurable via DB_POOL_TIMEOUT env var
    pool_recycle=DB_POOL_RECYCLE,   # Configurable via DB_POOL_RECYCLE env var
    pool_pre_ping=True,             # Verify connections before use
    connect_args={
        "sslmode": "prefer",        # Use SSL when available but don't require it
        "connect_timeout": DB_CONNECT_TIMEOUT,  # Configurable via DB_CONNECT_TIMEOUT env var
        "application_name": "epic_embedder"  # Identify embedder in database logs
    }
)

# Set timeouts after connection establishment to avoid Azure PostgreSQL startup parameter issues
@event.listens_for(engine, "connect")
def set_timeouts(dbapi_connection, connection_record):
    """Set statement and lock timeouts after connection establishment."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET statement_timeout = '300s'")  # 5 minute query timeout
        cursor.execute("SET lock_timeout = '60s'")        # 1 minute lock timeout

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