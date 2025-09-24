"""Service for managing statistics and processing information from the vector search API.

This service provides methods to retrieve system-wide, per-project, and filtered processing statistics
by wrapping the VectorSearchClient stats endpoints. Project lists and document types are now accessed
directly through the tools endpoints for better performance.
"""

import time
from datetime import datetime, timezone
from flask import current_app
from search_api.clients.vector_search_client import VectorSearchClient
from ..utils.cache import cache_with_ttl

class StatsService:
    """Service class for handling statistics operations."""

    @classmethod
    def get_processing_stats(cls, project_ids=None):
        """Get processing statistics for all projects.
        Args:
            project_ids (list, optional): DEPRECATED - No longer supported by vector API. All projects returned.
        Returns:
            dict: Response containing:
                - result.processing_stats: Statistics data from the vector search API
                - result.projects: Per-project statistics with total_files, successful_files, failed_files, skipped_files, and success_rate
                - result.summary: Aggregate metrics including total_skipped_files across all projects
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        if project_ids:
            current_app.logger.warning(f"project_ids parameter ({project_ids}) is deprecated and ignored. Vector API returns all projects.")
        
        stats = VectorSearchClient.get_processing_stats()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        # Add metrics to the existing response and wrap in result
        if stats:
            stats["metrics"] = metrics
            return {"result": stats}
        else:
            return {"result": {"metrics": metrics}}

    @classmethod
    def get_project_details(cls, project_id):
        """Get detailed processing logs for a specific project.
        Args:
            project_id (str): The project ID to get details for
        Returns:
            dict: Response containing:
                - result.project_details: Project-specific processing logs and data
                - result.processing_logs: Array of document processing records (if available)
                - result.project_id: The requested project ID (if available)
                - result.summary: Project summary including total_files, successful_files, failed_files, skipped_files, and success_rate
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        details = VectorSearchClient.get_project_details(project_id)
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        # Add metrics to the existing response and wrap in result
        if details:
            details["metrics"] = metrics
            return {"result": details}
        else:
            return {"result": {"metrics": metrics}}

    @classmethod
    def get_system_summary(cls):
        """Get high-level processing summary across the entire system.
        Returns:
            dict: Response containing:
                - result.summary: High-level aggregate metrics including total_skipped_files from the vector search API
                - result.total_projects: Number of projects (if available)
                - result.total_documents: Number of documents processed (if available)
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        summary = VectorSearchClient.get_system_summary()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        # Add metrics to the existing response and wrap in result
        if summary:
            summary["metrics"] = metrics
            return {"result": summary}
        else:
            return {"result": {"metrics": metrics}}
