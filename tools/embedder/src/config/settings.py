import os

from functools import lru_cache
from dotenv import load_dotenv
from pydantic import BaseModel, Field

"""
Settings configuration module for the EPIC.search Embedder.

This module defines configuration classes using Pydantic models for type safety and validation.
It loads environment variables using dotenv and provides a cached settings instance
through the get_settings function.
"""

load_dotenv()

class EmbeddingModelSettings(BaseModel):
    """
    Configuration settings for the embedding model.
    
    Attributes:
        model_name (str): Name of the sentence transformer model to use for document embeddings
    """
    model_name: str = Field(default_factory=lambda:
        os.environ.get("EMBEDDING_MODEL_NAME", "all-mpnet-base-v2")
    )

class KeywordExtractionSettings(BaseModel):
    """
    Configuration settings for the keyword extraction model.
    
    Attributes:
        model_name (str): Name of the sentence transformer model to use for keyword extraction
    """
    model_name: str = Field(default_factory=lambda:
        os.environ.get("KEYWORD_MODEL_NAME", "all-mpnet-base-v2")
    )

class LoggingDatabaseSettings(BaseModel):
    """
    Configuration for the logging database connection.
    
    Attributes:
        db_url (str): Database connection URL for the processing logs database
    """
    db_url: str = Field(default_factory=lambda: os.getenv("LOGS_DATABASE_URL"))

class VectorStoreSettings(BaseModel):
    """
    Configuration for the vector database.
    
    Attributes:
        db_url (str): Database connection URL for the vector database
        embedding_dimensions (int): Dimensionality of the embeddings
        auto_create_extension (bool): Whether to automatically create the pgvector extension
        reset_db (bool): Whether to drop and recreate all tables on startup (dev/test only)
    """
    db_url: str = Field(default_factory=lambda: os.getenv("VECTOR_DB_URL"))
    embedding_dimensions: int = os.environ.get("EMBEDDING_DIMENSIONS", 768)
    auto_create_extension: bool = Field(default_factory=lambda: os.environ.get("AUTO_CREATE_PGVECTOR_EXTENSION", "True").lower() in ("true", "1", "yes"))
    reset_db: bool = Field(default_factory=lambda: os.environ.get("RESET_DB", "False").lower() in ("true", "1", "yes"))

class ChunkSettings(BaseModel):
    """
    Configuration for document chunking behavior.
    
    Attributes:
        chunk_size (int): Size of text chunks in characters
        chunk_overlap (int): Number of characters to overlap between consecutive chunks
    """
    chunk_size: int = Field(default_factory=lambda: os.environ.get("CHUNK_SIZE", 1000))
    chunk_overlap: int = Field(default_factory=lambda: os.environ.get("CHUNK_OVERLAP", 200))


class MultiProcessingSettings(BaseModel):
    """
    Configuration for parallel processing.
    
    Attributes:
        files_concurrency_size (int): Number of files to process in parallel
    """
    files_concurrency_size: int = Field(default_factory=lambda: os.environ.get("FILES_CONCURRENCY_SIZE", 4))


class S3Settings(BaseModel):
    """
    Configuration for S3 storage connection.
    
    Attributes:
        bucket_name (str): Name of the S3 bucket
        region_name (str): S3 region for the S3 bucket
        access_key_id (str): S3 access key ID
        secret_access_key (str): S3 secret access key
        endpoint_uri (str): Endpoint URI for S3-compatible storage
    """
    bucket_name: str = Field(default_factory=lambda: os.getenv("S3_BUCKET_NAME"))
    region_name: str = Field(default_factory=lambda: os.getenv("S3_REGION_NAME"))
    access_key_id: str = Field(default_factory=lambda: os.getenv("S3_ACCESS_KEY_ID"))
    secret_access_key: str = Field(
        default_factory=lambda: os.getenv("S3_SECRET_ACCESS_KEY")
    )
    endpoint_uri: str = Field(default_factory=lambda: os.getenv("S3_ENDPOINT_URI"))

class DocumentSearchSettings(BaseModel):
    """
    Configuration for the document search API.
    
    Attributes:
        document_search_url (str): Base URL for the document search API
    """
    document_search_url: str = Field(default_factory=lambda: os.getenv("DOCUMENT_SEARCH_URL"))


class Settings(BaseModel):
    """
    Main settings class that combines all configuration categories.
    
    This class aggregates all the specialized setting classes into a single
    configuration object for the application.
    
    Attributes:
        embedding_model_settings (EmbeddingModelSettings): Settings for the embedding model
        keyword_extraction_settings (KeywordExtractionSettings): Settings for the keyword extraction model
        vector_store_settings (VectorStoreSettings): Settings for the vector database
        multi_processing_settings (MultiProcessingSettings): Settings for parallel processing
        s3_settings (S3Settings): Settings for S3 storage
        chunk_settings (ChunkSettings): Settings for document chunking
        logging_db_settings (LoggingDatabaseSettings): Settings for the logging database
        document_search_settings (DocumentSearchSettings): Settings for the document search API
    """
    embedding_model_settings: EmbeddingModelSettings = Field(
        default_factory=EmbeddingModelSettings
    )
    keyword_extraction_settings: KeywordExtractionSettings = Field(
        default_factory=KeywordExtractionSettings
    )
    vector_store_settings: VectorStoreSettings = Field(
        default_factory=VectorStoreSettings
    )
    multi_processing_settings: MultiProcessingSettings = Field(
        default_factory=MultiProcessingSettings
    )
    s3_settings: S3Settings = Field(default_factory=S3Settings)
    chunk_settings: ChunkSettings = Field(default_factory=ChunkSettings)
    logging_db_settings: LoggingDatabaseSettings = Field(
        default_factory=LoggingDatabaseSettings
    )
    document_search_settings: DocumentSearchSettings = Field(
        default_factory=DocumentSearchSettings
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get the application settings, using cached values if available.
    
    This function is decorated with lru_cache to ensure settings are only loaded once
    per application instance, improving performance.
    
    Returns:
        Settings: The application settings object
    """
    settings = Settings()
    return settings
