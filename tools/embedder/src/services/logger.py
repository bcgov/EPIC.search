from src.models import get_session
from src.models  import ProcessingLog
from src.schemas import ProcessingLogSchema
from datetime import datetime

def log_processing_result(project_id, document_id, status):
    session = get_session()
    record = ProcessingLog(
        project_id=project_id,
        document_id=document_id,
        status=status,
        processed_at=datetime.utcnow()
    )
    session.add(record)
    session.commit()

def get_processing_logs(project_id=None):
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
    session = get_session()
    query = session.query(ProcessingLog).filter(ProcessingLog.status == 'success')
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    results = query.all()
    session.close()

    schema = ProcessingLogSchema(many=True)
    return schema.dump(results)

def load_incomplete_files(project_id=None):
    session = get_session()
    query = session.query(ProcessingLog).filter(ProcessingLog.status == 'failure')
    if project_id:
        query = query.filter(ProcessingLog.project_id == project_id)
    
    results = query.all()
    session.close()

    schema = ProcessingLogSchema(many=True)
    return schema.dump(results) 
