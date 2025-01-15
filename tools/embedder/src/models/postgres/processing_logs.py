import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProcessingLog(Base):
    __tablename__ = 'processing_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False)
    document_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # e.g. "success" or "failure"
    processed_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
