"""Service for managing statistics and processing information from the vector search API.

This service provides methods to retrieve system-wide, per-project, and filtered processing statistics
by wrapping the VectorSearchClient stats endpoints.
"""

import time
from datetime import datetime, timezone
from flask import current_app
from .vector_search_client import VectorSearchClient

class StatsService:
    """Service class for handling statistics and processing info operations."""

    @classmethod
    def get_processing_stats(cls, project_ids=None):
        """Get processing statistics for all projects or filtered by project IDs.
        Args:
            project_ids (list, optional): List of project IDs to filter by.
        Returns:
            dict: Processing statistics and performance metrics.
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        stats = VectorSearchClient.get_processing_stats(project_ids)
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return {"result": {"processing_stats": stats, "metrics": metrics}}

    @classmethod
    def get_project_details(cls, project_id):
        """Get detailed processing logs for a specific project.
        Args:
            project_id (str): The project ID to get details for
        Returns:
            dict: Project details and performance metrics.
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        details = VectorSearchClient.get_project_details(project_id)
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return {"result": {"project_details": details, "metrics": metrics}}

    @classmethod
    def get_system_summary(cls):
        """Get high-level processing summary across the entire system.
        Returns:
            dict: System summary and performance metrics.
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        summary = VectorSearchClient.get_system_summary()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return {"result": {"system_summary": summary, "metrics": metrics}}
