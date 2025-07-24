# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This exports all of the models and schemas used by the application."""


from .pgvector.vector_db_utils import init_vec_db, SessionLocal
from .pgvector.vector_store import VectorStore
from .pgvector.vector_models import DocumentChunk, Document, Project, ProcessingLog, Base
from .pgvector import VectorStore as PgVectorStore

def get_session():
    """Return a new SQLAlchemy session for database operations with proper error handling."""
    from sqlalchemy import text
    
    session = SessionLocal()
    try:
        # Configure session for better error handling
        session.execute(text("SET statement_timeout = '300s'"))  # 5 minute query timeout
        session.execute(text("SET lock_timeout = '60s'"))       # 1 minute lock timeout
        return session
    except Exception as e:
        session.close()
        raise e

def get_db_session():
    """Context manager for database sessions with automatic cleanup."""
    from contextlib import contextmanager
    
    @contextmanager
    def _session_context():
        session = get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    return _session_context()
