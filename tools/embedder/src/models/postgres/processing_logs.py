import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

"""
Processing Logs Database Model module.

This module defines the database model for tracking document processing status.
It uses SQLAlchemy ORM to define a ProcessingLog table that records which documents
have been processed and whether the processing was successful or not.
"""

Base = declarative_base()

class ProcessingLog(Base):
    """
    SQLAlchemy model for the processing_logs table.
    
    This class defines the structure of the processing_logs table,
    which tracks the processing status of documents in the system.
    
    Attributes:
        id (int): Primary key, auto-incrementing identifier
        project_id (str): ID of the project the document belongs to
        document_id (str): ID of the document that was processed
        status (str): Status of the processing operation ("success" or "failure")
        processed_at (datetime): Timestamp when the document was processed
    """
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False)
    document_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # e.g. "success" or "failure"
    processed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
