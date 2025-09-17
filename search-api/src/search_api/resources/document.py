"""API endpoints for managing document resources."""

import hashlib
import mimetypes
import os

from http import HTTPStatus
from flask import Response, current_app, request
from flask_restx import Namespace, Resource
from urllib.parse import unquote
from search_api.utils.util import cors_preflight
from search_api.services.s3_reader import read_file_from_s3
from search_api.exceptions import ResourceNotFoundError
from search_api.schemas.document import DocumentDownloadSchema
# from search_api.auth import auth
from search_api.auth import auth
from .apihelper import Api as ApiHelper

API = Namespace("document", description="Endpoints for Document Operations")

# Add a simple log to verify the namespace is being loaded
from flask import current_app
import logging
logger = logging.getLogger(__name__)
logger.info("Document namespace module loaded")

def detect_mimetype(file_name, file_data=None):
    """
    Detect the MIME type of a file based on its filename and optionally file content.
    
    Args:
        file_name (str): The name of the file including extension
        file_data (bytes, optional): The actual file content for content-based detection
    
    Returns:
        str: The detected MIME type, defaults to 'application/octet-stream' if unknown
    """
    # First try to detect based on file extension
    mimetype, _ = mimetypes.guess_type(file_name)
    
    if mimetype:
        current_app.logger.info(f"Detected mimetype from filename '{file_name}': {mimetype}")
        return mimetype
    
    # If file extension detection fails, try content-based detection for common types
    if file_data:
        # Check for PDF signature
        if file_data.startswith(b'%PDF'):
            current_app.logger.info("Detected PDF from file content signature")
            return 'application/pdf'
        
        # Check for JPEG signatures
        elif file_data.startswith(b'\xff\xd8\xff'):
            current_app.logger.info("Detected JPEG from file content signature")
            return 'image/jpeg'
        
        # Check for PNG signature
        elif file_data.startswith(b'\x89PNG\r\n\x1a\n'):
            current_app.logger.info("Detected PNG from file content signature")
            return 'image/png'
        
        # Check for GIF signatures
        elif file_data.startswith(b'GIF87a') or file_data.startswith(b'GIF89a'):
            current_app.logger.info("Detected GIF from file content signature")
            return 'image/gif'
        
        # Check for DOCX (ZIP-based Office document)
        elif file_data.startswith(b'PK\x03\x04') and b'word/' in file_data[:1024]:
            current_app.logger.info("Detected DOCX from file content signature")
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        # Check for XLSX (ZIP-based Office document)
        elif file_data.startswith(b'PK\x03\x04') and b'xl/' in file_data[:1024]:
            current_app.logger.info("Detected XLSX from file content signature")
            return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        # Check for DOC (legacy Word document)
        elif file_data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            current_app.logger.info("Detected legacy Office document from file content signature")
            return 'application/msword'
        
        # Check for plain text
        elif all(byte < 128 for byte in file_data[:1024]):
            current_app.logger.info("Detected plain text from file content")
            return 'text/plain'
    
    # Default fallback
    current_app.logger.warning(f"Could not detect mimetype for '{file_name}', using default 'application/octet-stream'")
    return 'application/octet-stream'

document_download_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, DocumentDownloadSchema(), "DocumentDownload"
)

@cors_preflight("GET, OPTIONS")
@API.route("/view")
class DocumentDownload(Resource):    
    """Resource for document viewing.
    
    Provides an endpoint to view various document types stored in S3.
    Supports PDF, Word documents, Excel files, images (JPEG, PNG, GIF), and text files.
    The document is returned with appropriate headers for inline viewing (for supported types)
    or as downloadable attachments (for other types).
    
    The mimetype is automatically detected based on file extension and content analysis.
    
    Example:
        GET /api/document/view?key=path%2Fto%2Fdocument.pdf&file_name=document.pdf
        GET /api/document/view?key=path%2Fto%2Fimage.jpg&file_name=image.jpg
        GET /api/document/view?key=path%2Fto%2Fdocument.docx&file_name=document.docx
    """    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_app.logger.info("DocumentDownload resource initialized")    
    
    @staticmethod
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="View a document from S3 (supports PDF, Word, Excel, images, and text files)")    
    @API.param('key', 'The S3 key of the document to view (URL encoded)')
    @API.param('file_name', 'The filename to display in the browser (URL encoded)')
    @API.response(200, "Document content with appropriate mimetype")
    @API.response(304, "Not Modified (cached version is current)")
    @API.response(400, "Bad Request")
    @API.response(404, "Document Not Found")
    @API.response(500, "Internal Server Error")
    def get():
        """View a document from S3 storage with automatic mimetype detection."""
        current_app.logger.info("=== Document view request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Request path: {request.path}")
        current_app.logger.info(f"Request method: {request.method}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Request args: {dict(request.args)}")
        current_app.logger.info(f"Request environ keys: {list(request.environ.keys())}")
        
        # Log proxy-related headers specifically
        proxy_headers = ['X-Forwarded-For', 'X-Forwarded-Proto', 'X-Forwarded-Host', 'X-Real-IP', 'Host']
        for header in proxy_headers:
            value = request.headers.get(header)
            if value:
                current_app.logger.info(f"Proxy header {header}: {value}")
        
        try:
            # Get and decode query parameters
            s3_key = request.args.get('key')
            file_name = request.args.get('file_name')
            
            current_app.logger.info(f"Raw parameters - s3_key: {s3_key}, file_name: {file_name}")
            
            if not s3_key or not file_name:
                current_app.logger.error("Missing required parameters in request")
                raise ResourceNotFoundError("Missing required parameters")

            # URL decode the parameters since they're encoded
            s3_key = unquote(s3_key)
            file_name = unquote(file_name)
            
            current_app.logger.info(f"Decoded parameters - s3_key: {s3_key}, file_name: {file_name}")
            
            # Validate the parameters
            current_app.logger.info("Validating parameters with DocumentDownloadSchema")
            validation_result = DocumentDownloadSchema().load({
                "key": s3_key,
                "file_name": file_name
            })
            current_app.logger.info(f"Validation successful: {validation_result}")
            
            try:
                current_app.logger.info(f"Attempting to read file from S3: {s3_key}")
                
                # Get the file from S3
                file_data = read_file_from_s3(s3_key)
                current_app.logger.info(f"Successfully read file from S3. File size: {len(file_data)} bytes")
                
                # Generate ETag from file content
                current_app.logger.info("Generating ETag for file")
                file_hash = hashlib.md5(file_data).hexdigest()
                current_app.logger.info(f"Generated ETag: {file_hash}")
                
                # Check if the client has a cached version
                if_none_match = request.headers.get('If-None-Match')
                current_app.logger.info(f"Client If-None-Match header: {if_none_match}")
                if if_none_match and if_none_match == file_hash:
                    current_app.logger.info("File not modified, returning 304")
                    return Response(status=304)  # Not Modified
                
                # Create response with the file data
                current_app.logger.info("Creating response with file data")
                
                # Detect the actual mimetype based on filename and file content
                detected_mimetype = detect_mimetype(file_name, file_data)
                current_app.logger.info(f"Using mimetype: {detected_mimetype}")
                
                # Determine Content-Disposition based on file type
                # Use 'inline' for viewable types (PDF, images) and 'attachment' for downloadable types
                viewable_types = [
                    'application/pdf', 
                    'image/jpeg', 
                    'image/png', 
                    'image/gif', 
                    'text/plain'
                ]
                disposition = 'inline' if detected_mimetype in viewable_types else 'attachment'
                
                # For large files, we might want to stream the response
                # But for now, return the full file data
                response = Response(
                    file_data,
                    mimetype=detected_mimetype,
                    headers={
                        'Content-Disposition': f'{disposition}; filename="{file_name}"',
                        'Content-Length': str(len(file_data)),
                        'Cache-Control': 'public, max-age=3600, immutable',  # Cache for 1 hour
                        'ETag': file_hash,
                        'Accept-Ranges': 'bytes'  # Enable range requests
                    }
                )
                
                current_app.logger.info(f"Response created with {len(file_data)} bytes")
                current_app.logger.info("Document view request completed successfully")
                current_app.logger.info("=== Document view request ended ===")
                return response
                
            except Exception as e:
                current_app.logger.error(f"Error retrieving document from S3: {str(e)}")
                current_app.logger.error(f"S3 error type: {type(e).__name__}")
                current_app.logger.error(f"S3 key attempted: {s3_key}")
                import traceback
                current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
                raise ResourceNotFoundError("Document not found or inaccessible")
                
        except ResourceNotFoundError as e:
            current_app.logger.error(f"ResourceNotFoundError: {str(e)}")
            current_app.logger.error("=== Document view request ended with ResourceNotFoundError ===")
            raise e
        except Exception as e:
            current_app.logger.error(f"Document view error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Document view request ended with error ===")
            error_response = {"error": "An internal error has occurred. Please try again later."}
            return Response(
                error_response,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype='application/json'
            )
