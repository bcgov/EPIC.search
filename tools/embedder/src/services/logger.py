from src.models import get_session
from src.models  import ProcessingLog
from src.schemas import ProcessingLogSchema
from datetime import datetime

def log_processing_result(project_id, document_id, status):
    """
    Log the result of processing a document to the database.
    If a record for the same project_id and document_id exists, update it; otherwise, insert a new record.
    
    Args:
        project_id (str): The ID of the project the document belongs to
        document_id (str): The ID of the document that was processed
        status (str): The status of the processing operation ('success' or 'failure')
        
    Returns:
        None: The result is stored in the database
    """
    session = get_session()
    record = session.query(ProcessingLog).filter_by(project_id=project_id, document_id=document_id).first()
    if record:
        record.status = status
        record.processed_at = datetime.utcnow()
    else:
        record = ProcessingLog(
            project_id=project_id,
            document_id=document_id,
            status=status,
            processed_at=datetime.utcnow()
        )
        session.add(record)
    session.commit()

def get_processing_logs(project_id=None):
    """
    Retrieve processing logs from the database.
    
    Args:
        project_id (str, optional): Filter logs by project ID. If None, returns all logs.
        
    Returns:
        list: List of processing log dictionaries
    """
    session = get_session()
    query = session.query(ProcessingLog)
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    results = query.all()
    session.close()
    
    schema = ProcessingLogSchema(many=True)  
    logs_as_dicts = schema.dump(results)
    return logs_as_dicts

def load_completed_files(project_id=None):
    """
    Load information about successfully processed files from the database.
    
    Args:
        project_id (str, optional): Filter by project ID. If None, returns completed files for all projects.
        
    Returns:
        list: List of dictionaries containing information about successfully processed files
    """
    session = get_session()
    query = session.query(ProcessingLog).filter(ProcessingLog.status == 'success')
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    results = query.all()
    session.close()

    schema = ProcessingLogSchema(many=True)
    return schema.dump(results)

def load_incomplete_files(project_id=None):
    """
    Load information about files that failed processing.
    
    Args:
        project_id (str, optional): Filter by project ID. If None, returns failed files for all projects.
        
    Returns:
        list: List of dictionaries containing information about files that failed processing
    """
    session = get_session()
    query = session.query(ProcessingLog).filter(ProcessingLog.status == 'failure')
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    results = query.all()
    session.close()

    schema = ProcessingLogSchema(many=True)
    return schema.dump(results)
