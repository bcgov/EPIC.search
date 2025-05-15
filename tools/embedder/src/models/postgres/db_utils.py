from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .processing_logs import Base

# Import path setup module
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings

"""
Database Utilities module for PostgreSQL.

This module provides utility functions for interacting with the PostgreSQL database
used for storing processing logs. It handles database connection setup, session management,
and database initialization.
"""

# Initialize settings at module level
settings = get_settings()

# Get database URL from settings
database_url = settings.logging_db_settings.db_url

if database_url and database_url.startswith('postgresql:'):
    database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')

engine = create_engine(database_url)
SessionLocal = sessionmaker(bind=engine)

def get_session():
    """
    Create and return a new SQLAlchemy database session.
    
    This function provides a way to get a database session for interacting
    with the processing logs database using SQLAlchemy ORM.
    
    Returns:
        sqlalchemy.orm.Session: A new SQLAlchemy database session
    """
    return SessionLocal()

def init_db():
    """
    Initialize the database by creating all tables defined in the models.
    
    This function creates all tables that have been defined using SQLAlchemy
    ORM models (like ProcessingLog). If the tables already exist, it will not
    recreate them or modify their structure.
    
    This should be called when the application starts to ensure the database
    schema is properly set up.
    
    Returns:
        None
    """
    Base.metadata.create_all(engine)
