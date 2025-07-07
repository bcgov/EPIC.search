from src.models.pgvector.vector_models import Project, Base
from sqlalchemy.orm import sessionmaker
from src.config.settings import get_settings
from sqlalchemy import create_engine

def upsert_project(project_id: str, project_name: str, project_metadata: dict = None):
    """
    Insert or update a project in the projects table using SQLAlchemy ORM.
    
    Args:
        project_id (str): The unique project identifier
        project_name (str): The project name
        project_metadata (dict, optional): Full project data from API to store as JSONB
    """
    settings = get_settings()
    database_url = settings.vector_store_settings.db_url
    if database_url and database_url.startswith('postgresql:'):
        database_url = database_url.replace('postgresql:', 'postgresql+psycopg:')
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        project = session.query(Project).filter_by(project_id=project_id).first()
        if project:
            project.project_name = project_name
            if project_metadata:
                project.project_metadata = project_metadata
        else:
            project = Project(
                project_id=project_id, 
                project_name=project_name,
                project_metadata=project_metadata
            )
            session.add(project)
        session.commit()
    except Exception as e:
        print(f"Error upserting project record: {e}")
        session.rollback()
    finally:
        session.close()
