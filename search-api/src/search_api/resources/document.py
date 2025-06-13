"""API endpoints for managing document resources."""

from http import HTTPStatus
from flask import Response, current_app, send_file, request
from flask_restx import Namespace, Resource
import io
from urllib.parse import unquote

from search_api.utils.util import cors_preflight
from search_api.services.s3_reader import read_file_from_s3
from search_api.exceptions import ResourceNotFoundError
from search_api.schemas.document import DocumentDownloadSchema
from search_api.auth import auth
from .apihelper import Api as ApiHelper

API = Namespace("document", description="Endpoints for Document Operations")

document_download_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, DocumentDownloadSchema(), "DocumentDownload"
)

@cors_preflight("GET, OPTIONS")
@API.route("/view")
class DocumentDownload(Resource):    
    """Resource for document viewing.
      Provides an endpoint to view PDF documents stored in S3.
    The document is returned with headers set for inline viewing in a browser.
    
    Example:
        GET /api/document/view?key=path%2Fto%2Fdocument.pdf&file_name=document.pdf
    """    
    
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
        try:
            # Get and decode query parameters
            s3_key = request.args.get('key')
            file_name = request.args.get('file_name')
            
            if not s3_key or not file_name:
                raise ResourceNotFoundError("Missing required parameters")

            # URL decode the parameters since they're encoded
            s3_key = unquote(s3_key)
            file_name = unquote(file_name)
            
            # Validate the parameters
            DocumentDownloadSchema().load({
                "key": s3_key,
                "file_name": file_name
            })
            
            try:
                # Get the file from S3
                file_data = read_file_from_s3(s3_key)
                
                # Create response with the file data
                response = Response(
                    file_data,
                    mimetype='application/pdf',
                    headers={
                        'Content-Disposition': f'inline; filename="{file_name}"'
                    }
                )
                
                return response
                
            except Exception as e:
                current_app.logger.error(f"Error retrieving document from S3: {str(e)}")
                raise ResourceNotFoundError("Document not found or inaccessible")
                
        except Exception as e:
            current_app.logger.error(f"Document view error: {str(e)}")
            error_response = {"error": str(e)}
            return Response(
                error_response,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype='application/json'
            )
