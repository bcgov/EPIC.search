"""API endpoints for managing document resources."""

from http import HTTPStatus
from flask import Response, current_app, send_file, request
from flask_restx import Namespace, Resource
import io
import os

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
@API.route("/download")
class DocumentDownload(Resource):
    """Resource for document downloads."""    
    
    @staticmethod
    # @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Download a document from S3")
    @API.param('key', 'The S3 key of the document to download', _in='query')
    @API.response(400, "Bad Request")
    @API.response(404, "Document Not Found")
    @API.response(500, "Internal Server Error")
    def get():
        """Download a document from S3 storage."""
        try:            # Get the S3 key from query parameters and decode it
            s3_key = request.args.get('key')
            if not s3_key:
                raise ResourceNotFoundError("No document key provided")
            
            # URL decode the key since it was encoded by the caller
            try:
                from urllib.parse import unquote
                s3_key = unquote(s3_key)
            except Exception as e:
                current_app.logger.error(f"Error decoding S3 key: {str(e)}")
                
            # Validate the parameters
            DocumentDownloadSchema().load({
                "s3_key": s3_key
            })
            
            try:
                # Get the file from S3
                file_data = read_file_from_s3(s3_key)
                
                # Create an in-memory file-like object
                file_obj = io.BytesIO(file_data)
                
                # Get the filename from the last part of the S3 key
                filename = os.path.basename(s3_key)
                
                # Send the file
                return send_file(
                    file_obj,
                    download_name=filename,
                    mimetype='application/pdf',
                    as_attachment=True
                )
                
            except Exception as e:
                current_app.logger.error(f"Error retrieving document from S3: {str(e)}")
                raise ResourceNotFoundError("Document not found or inaccessible")
                
        except Exception as e:
            current_app.logger.error(f"Document download error: {str(e)}")
            error_response = {"error": str(e)}
            return Response(
                response=error_response,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype='application/json'
            )
