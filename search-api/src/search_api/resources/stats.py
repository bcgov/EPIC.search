from flask import Response, request, current_app
from flask_restx import Namespace, Resource
from http import HTTPStatus
import time
import json

from ..services.stats_service import StatsService
from search_api.auth import auth
from .apihelper import Api as ApiHelper
from search_api.utils.util import cors_preflight

import json

API = Namespace("stats", description="Endpoints for Search")
"""Custom exception messages
"""

@cors_preflight("GET, OPTIONS")
@API.route("/processing", methods=["GET", "OPTIONS"])
class StatsProcessing(Resource):
    @staticmethod
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get processing statistics for all or specific projects including successful, failed, and skipped file counts")
    def get():
        current_app.logger.info("=== Stats processing GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_processing_stats()")
            start_time = time.time()
            result = StatsService.get_processing_stats()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_processing_stats completed in {(end_time - start_time):.2f} seconds")
            current_app.logger.info(f"Processing stats result count: {len(result) if isinstance(result, (list, dict)) else 'Unknown'}")
            current_app.logger.info("=== Stats processing GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats processing GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Stats processing GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get processing stats"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/processing/<string:project_id>", methods=["GET", "OPTIONS"])
class StatsProject(Resource):
    @staticmethod
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get detailed processing logs for a specific project")
    def get(project_id):
        current_app.logger.info("=== Stats project GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Project ID parameter: {project_id}")
        
        try:
            current_app.logger.info(f"Calling StatsService.get_project_details for project: {project_id}")
            start_time = time.time()
            result = StatsService.get_project_details(project_id)
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_project_details completed in {(end_time - start_time):.2f} seconds")
            current_app.logger.info(f"Project details result: {type(result).__name__} with {len(result) if isinstance(result, (list, dict)) else 'Unknown'} items")
            current_app.logger.info("=== Stats project GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats project GET error for project {project_id}: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Stats project GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get project details"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/summary", methods=["GET", "OPTIONS"])
class StatsSummary(Resource):
    @staticmethod
    @auth.require
    @ApiHelper.swagger_decorators(API, endpoint_description="Get high-level processing summary across entire system")
    def get():
        current_app.logger.info("=== Stats summary GET request started ===")
        current_app.logger.info(f"Request URL: {request.url}")
        
        try:
            current_app.logger.info("Calling StatsService.get_system_summary()")
            start_time = time.time()
            result = StatsService.get_system_summary()
            end_time = time.time()
            
            current_app.logger.info(f"StatsService.get_system_summary completed in {(end_time - start_time):.2f} seconds")
            current_app.logger.info(f"System summary result: {type(result).__name__}")
            current_app.logger.info("=== Stats summary GET request completed successfully ===")
            
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats summary GET error: {str(e)}")
            current_app.logger.error(f"Error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
            current_app.logger.error("=== Stats summary GET request ended with error ===")
            return Response(json.dumps({"error": "Failed to get system summary"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')
