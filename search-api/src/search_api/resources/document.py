"""API endpoints for managing document resources."""

import hashlib

from http import HTTPStatus
from flask import Response, current_app, request
from flask_restx import Namespace, Resource
from urllib.parse import unquote
from search_api.utils.util import cors_preflight
from search_api.services.s3_reader import read_file_from_s3
from search_api.exceptions import ResourceNotFoundError
from search_api.schemas.document import DocumentDownloadSchema
# from search_api.auth import auth
from .apihelper import Api as ApiHelper

API = Namespace("document", description="Endpoints for Document Operations")

# Add a simple log to verify the namespace is being loaded
from flask import current_app
import logging
logger = logging.getLogger(__name__)
logger.info("Document namespace module loaded")

document_download_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, DocumentDownloadSchema(), "DocumentDownload"
)

@cors_preflight("GET, OPTIONS")
@API.route("/health")
class DocumentHealth(Resource):
    """Simple health check for document endpoint."""
    
    @staticmethod
    def get():
        """Health check endpoint."""
        current_app.logger.info("Document health check endpoint called")
        return {"status": "ok", "service": "document"}, 200

@cors_preflight("GET, OPTIONS")
@API.route("/test")
class DocumentTest(Resource):
    """Simple test endpoint for document API."""
    
    @staticmethod
    def get():
        """Test endpoint - just returns success."""
        current_app.logger.info("Document test endpoint called successfully")
        return {"status": "ok", "message": "Document API is reachable"}, 200

@cors_preflight("GET, OPTIONS")
@API.route("/network-test")
class NetworkDiagnostic(Resource):
    """Network diagnostic endpoint to test S3 connectivity."""
    
    @staticmethod
    def get():
        """Test network connectivity to S3 endpoint."""
        current_app.logger.info("Network diagnostic endpoint called")
        
        import socket
        import requests
        import time
        
        results = {
            "timestamp": time.time(),
            "tests": {}
        }
        
        # Test 1: DNS Resolution
        try:
            ip_address = socket.gethostbyname('nrs.objectstore.gov.bc.ca')
            results["tests"]["dns_resolution"] = {
                "status": "success",
                "ip_address": ip_address
            }
        except Exception as e:
            results["tests"]["dns_resolution"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 2: TCP Connection
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            start_time = time.time()
            result = sock.connect_ex((ip_address, 443))
            end_time = time.time()
            sock.close()
            
            if result == 0:
                results["tests"]["tcp_connection"] = {
                    "status": "success",
                    "connection_time_ms": round((end_time - start_time) * 1000, 2)
                }
            else:
                results["tests"]["tcp_connection"] = {
                    "status": "failed",
                    "error_code": result
                }
        except Exception as e:
            results["tests"]["tcp_connection"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 3: HTTPS Request
        try:
            start_time = time.time()
            response = requests.get('https://nrs.objectstore.gov.bc.ca', timeout=30, verify=True)
            end_time = time.time()
            
            results["tests"]["https_request"] = {
                "status": "success",
                "status_code": response.status_code,
                "response_time_ms": round((end_time - start_time) * 1000, 2),
                "headers": dict(response.headers)
            }
        except Exception as e:
            results["tests"]["https_request"] = {
                "status": "failed",
                "error": str(e)
            }
        
        # Test 4: S3 Endpoint specific test
        s3_endpoint = current_app.config.get("S3_ENDPOINT_URI", "https://nrs.objectstore.gov.bc.ca")
        try:
            start_time = time.time()
            response = requests.get(s3_endpoint, timeout=30, verify=True)
            end_time = time.time()
            
            results["tests"]["s3_endpoint"] = {
                "status": "success",
                "endpoint": s3_endpoint,
                "status_code": response.status_code,
                "response_time_ms": round((end_time - start_time) * 1000, 2)
            }
        except Exception as e:
            results["tests"]["s3_endpoint"] = {
                "status": "failed",
                "endpoint": s3_endpoint,
                "error": str(e)
            }
        
        current_app.logger.info(f"Network diagnostic results: {results}")
        return results, 200

@cors_preflight("GET, OPTIONS")
@API.route("/config-check")
class ConfigCheck(Resource):
    """Configuration check endpoint."""
    
    @staticmethod
    def get():
        """Check S3 configuration (without exposing secrets)."""
        current_app.logger.info("Config check endpoint called")
        
        config_info = {
            "s3_endpoint_uri": current_app.config.get("S3_ENDPOINT_URI"),
            "s3_bucket_name": current_app.config.get("S3_BUCKET_NAME"),
            "s3_region": current_app.config.get("S3_REGION"),
            "s3_access_key_configured": bool(current_app.config.get("S3_ACCESS_KEY_ID")),
            "s3_secret_key_configured": bool(current_app.config.get("S3_SECRET_ACCESS_KEY")),
            "flask_env": current_app.config.get("FLASK_ENV"),
            "debug": current_app.debug
        }
        
        current_app.logger.info(f"Config check results: {config_info}")
        return config_info, 200

@cors_preflight("GET, OPTIONS")
@API.route("/view")
class DocumentDownload(Resource):    
    """Resource for document viewing.
      Provides an endpoint to view PDF documents stored in S3.
    The document is returned with headers set for inline viewing in a browser.
    
    Example:
        GET /api/document/view?key=path%2Fto%2Fdocument.pdf&file_name=document.pdf
    """    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_app.logger.info("DocumentDownload resource initialized")    
    
    @staticmethod
    # @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="View a document from S3")    
    @API.param('key', 'The S3 key of the document to view (URL encoded)')
    @API.param('file_name', 'The filename to display in the browser (URL encoded)')
    @API.response(400, "Bad Request")
    @API.response(404, "Document Not Found")
    @API.response(500, "Internal Server Error")
    def get():
        """View a document from S3 storage."""
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
                
                # For large files, we might want to stream the response
                # But for now, return the full file data
                response = Response(
                    file_data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'inline; filename="{file_name}"',
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
