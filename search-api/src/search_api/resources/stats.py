from flask import Response, request, current_app
from flask_restx import Namespace, Resource
from http import HTTPStatus
from ..services.stats_service import StatsService
from .apihelper import Api as ApiHelper
from search_api.utils.util import cors_preflight
from search_api.schemas.stats import StatsRequestSchema

import json

API = Namespace("stats", description="Endpoints for Search")
"""Custom exception messages
"""

search_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, StatsRequestSchema(), "Stats"
)

@cors_preflight("GET, OPTIONS, POST")
@API.route("/processing", methods=["GET", "POST", "OPTIONS"])
class StatsProcessing(Resource):
    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get processing statistics for all or specific projects")
    def get():
        try:
            result = StatsService.get_processing_stats()
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats processing GET error: {str(e)}")
            return Response(json.dumps({"error": "Failed to get processing stats"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get processing statistics for specific projects")
    def post():
        try:
            data = request.get_json(force=True)
            project_ids = data.get("projectIds", None)
            result = StatsService.get_processing_stats(project_ids)
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats processing POST error: {str(e)}")
            return Response(json.dumps({"error": "Failed to get processing stats"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/project/<string:project_id>", methods=["GET", "OPTIONS"])
class StatsProject(Resource):
    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get detailed processing logs for a specific project")
    def get(project_id):
        try:
            result = StatsService.get_project_details(project_id)
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats project GET error: {str(e)}")
            return Response(json.dumps({"error": "Failed to get project details"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')

@cors_preflight("GET, OPTIONS")
@API.route("/summary", methods=["GET", "OPTIONS"])
class StatsSummary(Resource):
    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get high-level processing summary across entire system")
    def get():
        try:
            result = StatsService.get_system_summary()
            return Response(json.dumps(result), status=HTTPStatus.OK, mimetype='application/json')
        except Exception as e:
            current_app.logger.error(f"Stats summary GET error: {str(e)}")
            return Response(json.dumps({"error": "Failed to get system summary"}), status=HTTPStatus.INTERNAL_SERVER_ERROR, mimetype='application/json')
