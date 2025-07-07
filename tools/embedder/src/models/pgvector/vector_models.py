"""
Vector Models for pgvector-powered semantic search and analytics.

Defines all ORM models for:
- DocumentChunk: stores chunk content, metadata, and vector embedding
- Document: stores document-level tags, keywords, headings, and semantic embedding
- Project: stores project metadata
- ProcessingLog: stores structured processing metrics and status

All models use SQLAlchemy ORM and are compatible with pgvector and HNSW indexes.

Embedding dimensions are dynamically set from the configuration (settings.py), defaulting to 768.
"""

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.declarative import declarative_base
from src.config.settings import get_settings

settings = get_settings()
EMBEDDING_DIM = int(getattr(settings.vector_store_settings, 'embedding_dimensions', 768))

Base = declarative_base()

class DocumentChunk(Base):
    """
    ORM model for the document_chunks table.
    Stores chunk content, metadata, and pgvector embedding for semantic search.
    Embedding dimension is configurable via settings.
    """
    __tablename__ = 'document_chunks'
    id = Column(Integer, primary_key=True, autoincrement=True)
    embedding = Column(Vector(EMBEDDING_DIM))  # Use pgvector extension, configurable dimensions
    chunk_metadata = Column('metadata', JSONB)  # Renamed to avoid reserved name
    content = Column(Text)
    document_id = Column(String)
    project_id = Column(String)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (
        Index('ix_document_chunks_project_id', 'project_id'),
        # Removed HNSW index on embedding; now created via raw SQL in init_vec_db
    )

class Document(Base):
    """
    ORM model for the documents table.
    Stores document-level tags, keywords, headings, project, and semantic embedding.
    Embedding dimension is configurable via settings.
    """
    __tablename__ = 'documents'
    document_id = Column(String, primary_key=True)
    document_tags = Column(JSONB)
    document_keywords = Column(JSONB)
    document_headings = Column(JSONB)
    project_id = Column(String)
    embedding = Column(Vector(EMBEDDING_DIM))  # Configurable dimensions
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (
        Index('ix_documents_tags', 'document_tags', postgresql_using='gin'),
        Index('ix_documents_keywords', 'document_keywords', postgresql_using='gin'),
        Index('ix_documents_headings', 'document_headings', postgresql_using='gin'),
        Index('ix_documents_project_id', 'project_id'),
        # Removed HNSW index on document_embedding; now created via raw SQL in init_vec_db
    )

class Project(Base):
    """
    ORM model for the projects table.
    Stores project metadata including full project data from the API.
    """
    __tablename__ = 'projects'
    project_id = Column(String, primary_key=True)
    project_name = Column(String)
    project_metadata = Column(JSONB)  # Stores full project data from API
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    __table_args__ = (
        Index('ix_projects_metadata', 'project_metadata', postgresql_using='gin'),
    )

class ProcessingLog(Base):
    """
    ORM model for the processing_logs table.
    Stores per-document processing status and structured metrics as JSONB.
    """
    __tablename__ = 'processing_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False)
    document_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # e.g. "success" or "failure"
    processed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    metrics = Column(JSONB, nullable=True)  # Stores per-method timing metrics as JSONB
