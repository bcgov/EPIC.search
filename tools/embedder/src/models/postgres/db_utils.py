from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .processing_logs import Base, ProcessingLog
import os

DATABASE_URL =   os.environ.get("POSTGRES_LOG_DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_session():
    return SessionLocal()

def init_db():
    Base.metadata.create_all(engine)
