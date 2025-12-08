"""Resources for project and document type information from the vector API.

This module provides endpoints for retrieving project lists and document type information
from the vector search API directly for better performance and simpler architecture.
"""

from flask import Response, request, current_app
from flask_restx import Namespace, Resource
from http import HTTPStatus
import time
import json

from ..clients.vector_search_client import VectorSearchClient
from search_api.auth import auth
from .apihelper import Api as ApiHelper
from search_api.utils.util import cors_preflight

API = Namespace("tools", description="Tools and metadata endpoints")

@cors_preflight("GET, OPTIONS")
@API.route("/projects", methods=["GET", "OPTIONS"])
class ProjectsList(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get lightweight list of all projects")
    def get():
        """Get a lightweight list of all projects with IDs and names."""
        current_app.logger.info("=== Projects list GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling VectorSearchClient.get_projects_list()")
            start_time = time.time()
            projects_array = VectorSearchClient.get_projects_list()
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_projects_list completed in {(end_time - start_time):.2f} seconds")
            
            # Create simplified response format
            result = {
                "projects": projects_array,
                "total_projects": len(projects_array) if projects_array else 0
            }
            
            current_app.logger.info(f"Projects list result: {result['total_projects']} projects")
            current_app.logger.info("=== Projects list GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Projects list GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Projects list GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get projects list"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/document-types", methods=["GET", "OPTIONS"])
class DocumentTypes(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get all document types with metadata and aliases")
    def get():
        """Get all document types with names, aliases, and grouped legacy format."""
        current_app.logger.info("=== Document types GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling VectorSearchClient.get_document_types()")
            start_time = time.time()
            document_types_array = VectorSearchClient.get_document_types()
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_document_types completed in {(end_time - start_time):.2f} seconds")
            
            # Create simplified response format - return the normalized array directly
            result = {
                "document_types": document_types_array,
                "total_types": len(document_types_array) if document_types_array else 0
            }
            
            current_app.logger.info(f"Document types result: {result['total_types']} types")
            current_app.logger.info("=== Document types GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Document types GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Document types GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get document types"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/document-types/<string:type_id>", methods=["GET", "OPTIONS"])
class DocumentTypeDetails(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get detailed information for a specific document type")
    def get(type_id):
        """Get detailed information for a specific document type including aliases."""
        current_app.logger.info("=== Document type details GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Document type ID parameter: {type_id}")
        
        try:
            current_app.logger.info(f"Calling VectorSearchClient.get_document_type_details for type: {type_id}")
            start_time = time.time()
            doc_type_response = VectorSearchClient.get_document_type_details(type_id)
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_document_type_details completed in {(end_time - start_time):.2f} seconds")
            
            # Return single object directly (not in array) since this is for a specific document type ID
            if doc_type_response:
                current_app.logger.info(f"Document type details found for {type_id}")
            else:
                current_app.logger.warning(f"Document type {type_id} not found")
            
            current_app.logger.info("=== Document type details GET request completed successfully ===")
            
            return Response(json.dumps(doc_type_response), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Document type details GET error for type {type_id}: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Document type details GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get document type details"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("GET, OPTIONS")
@API.route("/search-strategies", methods=["GET", "OPTIONS"])
class SearchStrategies(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get available search strategies for search configuration")
    def get():
        """Get all available search strategies that can be used for query configuration."""
        current_app.logger.info("=== Search strategies GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling VectorSearchClient.get_search_strategies()")
            start_time = time.time()
            strategies_response = VectorSearchClient.get_search_strategies()
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_search_strategies completed in {(end_time - start_time):.2f} seconds")
            
            # Return response directly (not just the array) to match vector API format
            if strategies_response and "search_strategies" in strategies_response:
                strategy_count = len(strategies_response["search_strategies"])
                current_app.logger.info(f"Search strategies result: {strategy_count} strategies available")
            else:
                current_app.logger.warning("Search strategies response missing expected structure")
            
            current_app.logger.info("=== Search strategies GET request completed successfully ===")
            
            return Response(json.dumps(strategies_response), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Search strategies GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Search strategies GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get search strategies"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("GET, OPTIONS")
@API.route("/inference-options", methods=["GET", "OPTIONS"])
class InferenceOptions(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get available ML inference options and capabilities")
    def get():
        """Get all available ML inference options and capabilities for intelligent search."""
        current_app.logger.info("=== Inference options GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling VectorSearchClient.get_inference_options()")
            start_time = time.time()
            inference_response = VectorSearchClient.get_inference_options()
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_inference_options completed in {(end_time - start_time):.2f} seconds")
            
            # Return response directly (not wrapped in array) since this contains inference metadata
            if inference_response:
                current_app.logger.info("Inference options retrieved successfully")
            else:
                current_app.logger.warning("Inference options response was empty")
            
            current_app.logger.info("=== Inference options GET request completed successfully ===")
            
            return Response(json.dumps(inference_response), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Inference options GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Inference options GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get inference options"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')


@cors_preflight("GET, OPTIONS")
@API.route("/api-capabilities", methods=["GET", "OPTIONS"])
class ApiCapabilities(Resource):
    @staticmethod
    @auth.requires_epic_search_role(["viewer", "admin"])
    @ApiHelper.swagger_decorators(API, endpoint_description="Get complete API metadata and capabilities")
    def get():
        """Get comprehensive API metadata for adaptive clients and frontend integration."""
        current_app.logger.info("=== API capabilities GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling VectorSearchClient.get_api_capabilities()")
            start_time = time.time()
            capabilities_response = VectorSearchClient.get_api_capabilities()
            end_time = time.time()
            
            current_app.logger.info(f"VectorSearchClient.get_api_capabilities completed in {(end_time - start_time):.2f} seconds")
            
            # Return response directly (not wrapped in array) since this contains API metadata
            if capabilities_response:
                current_app.logger.info("API capabilities retrieved successfully")
            else:
                current_app.logger.warning("API capabilities response was empty")
            
            current_app.logger.info("=== API capabilities GET request completed successfully ===")
            
            return Response(json.dumps(capabilities_response), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"API capabilities GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== API capabilities GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get API capabilities"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')
