"""Statistics API endpoints for document processing metrics.

This module provides REST API endpoints for retrieving document processing
statistics and metrics. It includes endpoints for:

1. Processing statistics aggregated by project
2. Detailed processing logs for specific projects
3. Overall system processing metrics

The endpoints support optional project filtering and provide comprehensive
information about file processing success rates and error details.
"""

from http import HTTPStatus
from flask_restx import Namespace, Resource
from flask import Response
from marshmallow import EXCLUDE, Schema, fields
import json

from services.stats_service import StatsService
from .apihelper import Api as ApiHelper


class ProcessingStatsRequestSchema(Schema):
    """Schema for validating processing statistics requests.
    
    Defines the structure and validation rules for processing statistics requests,
    which retrieve aggregated processing metrics by project.
    
    Attributes:
        projectIds: Optional list of project IDs to filter results
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""
        unknown = EXCLUDE

    projectIds = fields.List(fields.Str(), data_key="projectIds", required=False, 
                           metadata={"description": "Optional list of project IDs to filter results. If not provided, returns stats for all projects."})


class ProjectDetailsRequestSchema(Schema):
    """Schema for validating project details requests.
    
    Defines the structure and validation rules for project details requests,
    which retrieve detailed processing logs for a specific project.
    
    Attributes:
        projectId: The required project ID to get detailed processing logs for
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """Exclude unknown fields in the deserialized output."""
        unknown = EXCLUDE

    projectId = fields.Str(data_key="projectId", required=True, 
                          metadata={"description": "Project ID to get detailed processing logs for"})


API = Namespace("stats", description="Endpoints for document processing statistics and metrics")

processing_stats_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, ProcessingStatsRequestSchema(), "Processing Statistics Request"
)

project_details_request_model = ApiHelper.convert_ma_schema_to_restx_model(
    API, ProjectDetailsRequestSchema(), "Project Details Request"
)


@API.route("/processing", methods=["GET", "POST", "OPTIONS"])
class ProcessingStats(Resource):
    """Processing statistics endpoint.
    
    Provides aggregated processing statistics across projects including
    total files processed, success rates, and failure counts.
    """

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get processing statistics aggregated by project")
    @API.response(400, "Bad Request")
    @API.response(200, "Statistics retrieved successfully")
    def get():
        """Get processing statistics for all projects.
        
        Retrieves aggregated processing statistics across all projects,
        including total files processed, success counts, failure counts,
        and success rates for each project.
        
        Returns:
            Response: JSON containing processing statistics:
                {
                    "processing_stats": {
                        "projects": [
                            {
                                "project_id": "uuid-string",
                                "project_name": "Project Name",
                                "total_files": 150,
                                "successful_files": 140,
                                "failed_files": 10,
                                "success_rate": 93.33
                            }
                        ],
                        "summary": {
                            "total_projects": 5,
                            "total_files_across_all_projects": 750,
                            "total_successful_files": 720,
                            "total_failed_files": 30,
                            "overall_success_rate": 96.0
                        }
                    }
                }
        """
        try:
            result = StatsService.get_processing_stats()
            return Response(
                response=json.dumps(result),
                status=HTTPStatus.OK,
                mimetype="application/json"
            )
        except Exception as e:
            error_response = {
                "error": "Failed to retrieve processing statistics",
                "details": str(e)
            }
            return Response(
                response=json.dumps(error_response),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get processing statistics for specific projects")
    @API.expect(processing_stats_request_model)
    @API.response(400, "Bad Request")
    @API.response(200, "Statistics retrieved successfully")
    def post():
        """Get processing statistics filtered by project IDs.
        
        Retrieves aggregated processing statistics for specified projects only.
        This allows filtering the statistics to focus on specific projects
        of interest while maintaining the same comprehensive metrics structure.
        
        The request body should contain:
        {
            "projectIds": ["project-uuid-1", "project-uuid-2"]
        }
        
        Returns:
            Response: JSON containing filtered processing statistics with the
                     same structure as the GET endpoint but limited to the
                     specified projects
        """
        try:
            request_data = ProcessingStatsRequestSchema().load(API.payload)
            project_ids = request_data.get("projectIds", None)
            
            result = StatsService.get_processing_stats(project_ids)
            return Response(
                response=json.dumps(result),
                status=HTTPStatus.OK,
                mimetype="application/json"
            )
        except Exception as e:
            error_response = {
                "error": "Failed to retrieve processing statistics",
                "details": str(e)
            }
            return Response(
                response=json.dumps(error_response),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )


@API.route("/project/<project_id>", methods=["GET", "OPTIONS"])
class ProjectProcessingDetails(Resource):
    """Project processing details endpoint.
    
    Provides detailed processing information for a specific project including
    individual file processing logs, timestamps, and error details.
    """

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get detailed processing logs for a specific project")
    @API.response(400, "Bad Request")
    @API.response(404, "Project not found")
    @API.response(200, "Project details retrieved successfully")
    def get(project_id):
        """Get detailed processing information for a specific project.
        
        Retrieves comprehensive processing logs for the specified project,
        including individual file processing records with timestamps,
        status information, and error details when applicable.
        
        Args:
            project_id (str): The UUID of the project to get details for
        
        Returns:
            Response: JSON containing detailed project processing information:
                {
                    "project_details": {
                        "project_id": "uuid-string",
                        "project_name": "Project Name",
                        "processing_logs": [
                            {
                                "log_id": "log-uuid",
                                "file_name": "document.pdf",
                                "status": "success",
                                "processed_at": "2024-01-15T10:30:00Z",
                                "error_message": null
                            }
                        ],
                        "summary": {
                            "total_files": 50,
                            "successful_files": 48,
                            "failed_files": 2,
                            "success_rate": 96.0
                        }
                    }
                }
        """
        try:
            result = StatsService.get_project_processing_details(project_id)
            
            # Check if project was found
            if result.get("project_details") is None:
                return Response(
                    response=json.dumps(result),
                    status=HTTPStatus.NOT_FOUND,
                    mimetype="application/json"
                )
            
            return Response(
                response=json.dumps(result),
                status=HTTPStatus.OK,
                mimetype="application/json"
            )
        except Exception as e:
            error_response = {
                "error": f"Failed to retrieve details for project {project_id}",
                "details": str(e)
            }
            return Response(
                response=json.dumps(error_response),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )


@API.route("/summary", methods=["GET", "OPTIONS"])
class ProcessingSummary(Resource):
    """Processing summary endpoint.
    
    Provides a high-level summary of processing statistics across the entire system.
    """

    @staticmethod
    @ApiHelper.swagger_decorators(API, endpoint_description="Get overall processing summary statistics")
    @API.response(400, "Bad Request")
    @API.response(200, "Summary statistics retrieved successfully")
    def get():
        """Get high-level processing summary statistics.
        
        Retrieves a concise summary of processing statistics across the entire
        system, providing key metrics for monitoring and reporting purposes.
        
        Returns:
            Response: JSON containing summary processing statistics:
                {
                    "processing_summary": {
                        "total_projects": 5,
                        "total_files_across_all_projects": 750,
                        "total_successful_files": 720,
                        "total_failed_files": 30,
                        "overall_success_rate": 96.0,
                        "projects_with_failures": 2,
                        "avg_success_rate_per_project": 95.5
                    }
                }
        """
        try:
            # Get full stats and extract summary
            full_stats = StatsService.get_processing_stats()
            summary = full_stats.get("processing_stats", {}).get("summary", {})
            projects = full_stats.get("processing_stats", {}).get("projects", [])
            
            # Calculate additional summary metrics
            projects_with_failures = len([p for p in projects if p.get("failed_files", 0) > 0])
            avg_success_rate = (
                sum(p.get("success_rate", 0) for p in projects) / len(projects)
                if projects else 0.0
            )
            
            enhanced_summary = {
                "processing_summary": {
                    **summary,
                    "projects_with_failures": projects_with_failures,
                    "avg_success_rate_per_project": round(avg_success_rate, 2)
                }
            }
            
            return Response(
                response=json.dumps(enhanced_summary),
                status=HTTPStatus.OK,
                mimetype="application/json"
            )
        except Exception as e:
            error_response = {
                "error": "Failed to retrieve processing summary",
                "details": str(e)
            }
            return Response(
                response=json.dumps(error_response),
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
                mimetype="application/json"
            )
