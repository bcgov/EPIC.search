"""Resources for project and document type information from the vector API.

This module provides endpoints for retrieving project lists and document type information
from the vector search API with caching for improved performance.
"""

from flask import Response, request, current_app
from flask_restx import Namespace, Resource
from http import HTTPStatus
import time
import json

from ..services.stats_service import StatsService
from search_api.auth import auth
from .apihelper import Api as ApiHelper
from search_api.utils.util import cors_preflight

API = Namespace("tools", description="Tools and metadata endpoints")

@cors_preflight("GET, OPTIONS")
@API.route("/projects", methods=["GET", "OPTIONS"])
class ProjectsList(Resource):
    @staticmethod
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get lightweight list of all projects")
    def get():
        """Get a lightweight list of all projects with IDs and names."""
        current_app.logger.info("=== Projects list GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_projects_list()")
            start_time = time.time()
            result = StatsService.get_projects_list()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_projects_list completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "projects" in result["result"]:
                project_count = result["result"]["total_projects"]
                current_app.logger.info(f"Projects list result: {project_count} projects")
            else:
                current_app.logger.warning("Projects list result missing expected structure")
            
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
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get all document types with metadata and aliases")
    def get():
        """Get all document types with names, aliases, and grouped legacy format."""
        current_app.logger.info("=== Document types GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_document_type_mappings()")
            start_time = time.time()
            result = StatsService.get_document_type_mappings()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_document_type_mappings completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "document_types" in result["result"]:
                type_count = result["result"]["total_types"]
                current_app.logger.info(f"Document types result: {type_count} types")
            else:
                current_app.logger.warning("Document types result missing expected structure")
            
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
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get detailed information for a specific document type")
    def get(type_id):
        """Get detailed information for a specific document type including aliases."""
        current_app.logger.info("=== Document type details GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Document type ID parameter: {type_id}")
        
        try:
            current_app.logger.info(f"Calling StatsService.get_document_type_details for type: {type_id}")
            start_time = time.time()
            result = StatsService.get_document_type_details(type_id)
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_document_type_details completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "document_type" in result["result"] and result["result"]["document_type"]:
                doc_type = result["result"]["document_type"]
                current_app.logger.info(f"Document type details result: {doc_type.get('name', 'Unknown')} with {len(doc_type.get('aliases', []))} aliases")
            else:
                current_app.logger.warning(f"Document type {type_id} not found or invalid response")
            
            current_app.logger.info("=== Document type details GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
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
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get available search strategies for search configuration")
    def get():
        """Get all available search strategies that can be used for query configuration."""
        current_app.logger.info("=== Search strategies GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_search_strategies()")
            start_time = time.time()
            result = StatsService.get_search_strategies()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_search_strategies completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "strategies" in result["result"]:
                strategy_count = len(result["result"]["strategies"])
                current_app.logger.info(f"Search strategies result: {strategy_count} strategies available")
            else:
                current_app.logger.warning("Search strategies result missing expected structure")
            
            current_app.logger.info("=== Search strategies GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
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
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get available ML inference options and capabilities")
    def get():
        """Get all available ML inference options and capabilities for intelligent search."""
        current_app.logger.info("=== Inference options GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_inference_options()")
            start_time = time.time()
            result = StatsService.get_inference_options()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_inference_options completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "inference_options" in result["result"]:
                options_count = len(result["result"]["inference_options"])
                current_app.logger.info(f"Inference options result: {options_count} options available")
            else:
                current_app.logger.warning("Inference options result missing expected structure")
            
            current_app.logger.info("=== Inference options GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
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
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get complete API metadata and capabilities")
    def get():
        """Get comprehensive API metadata for adaptive clients and frontend integration."""
        current_app.logger.info("=== API capabilities GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_api_capabilities()")
            start_time = time.time()
            result = StatsService.get_api_capabilities()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_api_capabilities completed in {(end_time - start_time):.2f} seconds")
            
            if "result" in result and "capabilities" in result["result"]:
                endpoints_count = len(result["result"]["capabilities"].get("endpoints", []))
                current_app.logger.info(f"API capabilities result: {endpoints_count} endpoints documented")
            else:
                current_app.logger.warning("API capabilities result missing expected structure")
            
            current_app.logger.info("=== API capabilities GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"API capabilities GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== API capabilities GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get API capabilities"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')
