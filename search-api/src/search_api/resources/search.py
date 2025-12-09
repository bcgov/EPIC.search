# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API endpoints for managing an search resource."""

from http import HTTPStatus
from flask_restx import Namespace, Resource
from flask import Response, current_app, request
import time
import json

from search_api.clients.vector_search_client import VectorSearchClient
from search_api.services.search_service import SearchService
from search_api.utils.util import cors_preflight
from search_api.schemas.search import SearchRequestSchema
from search_api.schemas.search import SimilaritySearchRequestSchema
from search_api.schemas.search import FeedbackSchema
from search_api.auth import auth
from .apihelper import Api as ApiHelper
from flask import Response, current_app

import json

API = Namespace("search", description="Endpoints for Search")
"""Custom exception messages
"""

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SearchRequestSchema(), "Search"
)

similar_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, SimilaritySearchRequestSchema(), "Search"
)

feedback_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, FeedbackSchema(), "Feedback"
)

@cors_preflight("POST, OPTIONS")
@API.route("/query", methods=["POST", "OPTIONS"])
class Search(Resource):
    """Resource for search."""    
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Search Query")
    @API.expect(search_request_model)
    @API.response(400, "Bad Request")
    @API.response(500, "Internal Server Error")
    def post():
        """Search"""
        current_app.logger.info("=== Search query request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Request payload: {API.payload}")
        
        try:
            request_data = SearchRequestSchema().load(API.payload)
            current_app.logger.info("Schema validation successful")
                        
            query = request_data.get("query", None)
            project_ids = request_data.get("projectIds", None)
            document_type_ids = request_data.get("documentTypeIds", None)
            inference = request_data.get("inference", None)
            ranking = request_data.get("ranking", None)
            search_strategy = request_data.get("searchStrategy", None)
            mode = request_data.get("mode", "rag")
            user_location = request_data.get("userLocation", None)
            
            # Extract new filtering parameters
            project_status = request_data.get("projectStatus", None)
            years = request_data.get("years", None)
            
            current_app.logger.info(f"Search parameters - Query: {query[:100] if query else None}{'...' if query and len(query) > 100 else ''}")
            current_app.logger.info(f"Search parameters - Project IDs: {project_ids}")
            current_app.logger.info(f"Search parameters - Document Type IDs: {document_type_ids}")
            current_app.logger.info(f"Search parameters - Project Status: {project_status}")
            current_app.logger.info(f"Search parameters - Years: {years}")
            current_app.logger.info(f"Search parameters - Inference: {inference}")
            current_app.logger.info(f"Search parameters - Ranking: {ranking}")
            current_app.logger.info(f"Search parameters - Search Strategy: {search_strategy}")
            current_app.logger.info(f"Search parameters - Processing Mode: {mode}")
            current_app.logger.info(f"Search parameters - User Location (from browser): {user_location}")

            current_app.logger.info("Calling SearchService.get_documents_by_query")
            start_time = time.time()
            documents = SearchService.get_documents_by_query(query, project_ids, document_type_ids, inference, ranking, search_strategy, mode, user_location, project_status, years)
            end_time = time.time()
            
            current_app.logger.info(f"SearchService completed in {(end_time - start_time):.2f} seconds")
            current_app.logger.info(f"Search results: {len(documents.get('documents', [])) if isinstance(documents, dict) else 'Unknown count'} documents returned")

            # ----------------------------
            # Create feedback session using VectorSearchClient
            # ----------------------------
            session_id = VectorSearchClient.create_feedback_session(
                query_text=query,
                project_ids=project_ids,
                document_type_ids=document_type_ids,
                search_result=documents
            )
            current_app.logger.info(f"Feedback session created: {session_id}")
            documents["feedback_session_id"] = session_id
            
            current_app.logger.info("=== Search query request completed successfully ===")
            
            return Response(json.dumps(documents), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            # Log the error internally
            current_app.logger.error(f"Search error occurred: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Search query request ended with error ===")
            # Return a generic error message
            error_response = {"error": "Internal server error occurred"}
            return Response(json.dumps(error_response), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("POST, OPTIONS")
@API.route("/document-similarity", methods=["POST", "OPTIONS"])
class DocumentSimilaritySearch(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Find documents similar to a specific document using document-level embeddings (new endpoint).")
    @API.expect(similar_request_model)
    def post():
        """Document-level embedding similarity search"""
        current_app.logger.info("=== Document similarity search request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        
        try:
            request_data = SimilaritySearchRequestSchema().load(API.payload)
            current_app.logger.info(f"Request payload: {request_data}")
            
            document_id = request_data["document_id"]
            project_ids = request_data.get("project_ids", None)
            limit = request_data.get("limit", 10)
            
            current_app.logger.info(f"Document similarity parameters - Document ID: {document_id}")
            current_app.logger.info(f"Document similarity parameters - Project IDs: {project_ids}")
            current_app.logger.info(f"Document similarity parameters - Limit: {limit}")
            
            current_app.logger.info("Calling SearchService.get_document_similarity")
            start_time = time.time()
            result = SearchService.get_document_similarity(document_id, project_ids, limit)
            end_time = time.time()
            
            current_app.logger.info(f"SearchService.get_document_similarity completed in {(end_time - start_time):.2f} seconds")
            current_app.logger.info(f"Document similarity results: {len(result.get('documents', [])) if isinstance(result, dict) else 'Unknown count'} documents returned")
            current_app.logger.info("=== Document similarity search request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Document similarity POST error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Document similarity search request ended with error ===")
            return Response(json.dumps({"error": "Failed to get document similarity"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("POST, PATCH, OPTIONS")
@API.route("/feedback", methods=["POST", "PATCH", "OPTIONS"])
class Feedback(Resource):
    """Endpoint to submit or update user feedback for search sessions."""

    @staticmethod
    @API.expect(feedback_model)
    @ApiHelper.swagger_decorators(API, endpoint_description="Submit or update search feedback")
    @API.response(400, "Bad Request")
    @API.response(200, "Feedback updated successfully")
    def post():
        """Create or update feedback for a search session."""
        try:
            data = request.get_json()
            if not data:
                return Response(
                    json.dumps({"error": "Invalid request payload"}),
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="application/json"
                )

            session_id = data.get("sessionId")
            feedback = data.get("feedback")
            comments = data.get("comments")

            if not session_id or not feedback:
                return Response(
                    json.dumps({"error": "Missing required parameters: sessionId and feedback"}),
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="application/json"
                )

            success = VectorSearchClient.update_feedback(
                session_id=session_id,
                feedback=feedback,
                comments=comments
            )

            if success:
                return Response(
                    json.dumps({"message": "Feedback updated successfully", "sessionId": session_id}),
                    status=HTTPStatus.OK,
                    mimetype="application/json"
                )
            else:
                return Response(
                    json.dumps({"error": "Failed to update feedback"}),
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    mimetype="application/json"
                )

        except Exception as e:
            current_app.logger.error(f"Error in feedback submission: {e}")
            return Response(
                json.dumps({"error": "Internal server error"}),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )

    @staticmethod
    def patch():
        """
        Explicit PATCH method to update feedback for an existing session.
        """
        try:
            data = request.get_json()
            if not data:
                return Response(
                    json.dumps({"error": "Invalid request payload"}),
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="application/json"
                )

            session_id = data.get("sessionId")
            feedback = data.get("feedback")
            comments = data.get("comments")

            if not session_id or not feedback:
                return Response(
                    json.dumps({"error": "Missing required parameters: sessionId and feedback"}),
                    status=HTTPStatus.BAD_REQUEST,
                    mimetype="application/json"
                )

            success = VectorSearchClient.update_feedback(
                session_id=session_id,
                feedback=feedback,
                comments=comments
            )

            if success:
                return Response(
                    json.dumps({"message": "Feedback updated successfully", "sessionId": session_id}),
                    status=HTTPStatus.OK,
                    mimetype="application/json"
                )
            else:
                return Response(
                    json.dumps({"error": "Failed to update feedback"}),
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                    mimetype="application/json"
                )

        except Exception as e:
            current_app.logger.error(f"Error in feedback PATCH: {e}")
            return Response(
                json.dumps({"error": "Internal server error"}),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )
