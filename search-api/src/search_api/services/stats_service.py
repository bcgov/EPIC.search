"""Service for managing statistics and processing information from the vector search API.

This service provides methods to retrieve system-wide, per-project, and filtered processing statistics
by wrapping the VectorSearchClient stats endpoints.
"""

import time
from datetime import datetime, timezone
from flask import current_app
from .vector_search_client import VectorSearchClient

class StatsService:
    @staticmethod
    def get_document_type_mappings():
        """Return document type mappings grouped by Act year (2002 and 2018)."""
        # Document type mappings for both 2002 Act and 2018 Act terms
        document_type_lookup = {
            # 2002 Act Terms
            "5cf00c03a266b7e1877504ca": "Request",
            "5cf00c03a266b7e1877504cb": "Letter",
            "5cf00c03a266b7e1877504cc": "Meeting Notes",
            "5cf00c03a266b7e1877504cd": "Comment Period",
            "5cf00c03a266b7e1877504ce": "Plan",
            "5cf00c03a266b7e1877504cf": "Report/Study",
            "5cf00c03a266b7e1877504d0": "Decision Materials",
            "5cf00c03a266b7e1877504d1": "Order",
            "5cf00c03a266b7e1877504d2": "Project Descriptions",
            "5cf00c03a266b7e1877504d3": "Application Information Requirement",
            "5cf00c03a266b7e1877504d4": "Application Materials",
            "5cf00c03a266b7e1877504d5": "Certificate Package",
            "5cf00c03a266b7e1877504d6": "Exception Package",
            "5cf00c03a266b7e1877504d7": "Amendment Package",
            "5cf00c03a266b7e1877504d9": "Inspection Record",
            "5cf00c03a266b7e1877504da": "Other",
            "5d0d212c7d50161b92a80ee3": "Comment/Submission",
            "5d0d212c7d50161b92a80ee4": "Tracking Table",
            "5d0d212c7d50161b92a80ee5": "Scientific Memo",
            "5d0d212c7d50161b92a80ee6": "Agreement",
            # 2018 Act Terms
            "5df79dd77b5abbf7da6f51bd": "Project Description",
            "5df79dd77b5abbf7da6f51be": "Letter",
            "5df79dd77b5abbf7da6f51bf": "Order",
            "5df79dd77b5abbf7da6f51c0": "Independent Memo",
            "5df79dd77b5abbf7da6f51c1": "Report/Study",
            "5df79dd77b5abbf7da6f51c2": "Management Plan",
            "5df79dd77b5abbf7da6f51c3": "Plan",
            "5df79dd77b5abbf7da6f51c4": "Tracking Table",
            "5df79dd77b5abbf7da6f51c5": "Ad/News Release",
            "5df79dd77b5abbf7da6f51c6": "Comment/Submission",
            "5df79dd77b5abbf7da6f51c7": "Comment Period",
            "5df79dd77b5abbf7da6f51c8": "Notification",
            "5df79dd77b5abbf7da6f51c9": "Application Materials",
            "5df79dd77b5abbf7da6f51ca": "Inspection Record",
            "5df79dd77b5abbf7da6f51cb": "Agreement",
            "5df79dd77b5abbf7da6f51cc": "Certificate Package",
            "5df79dd77b5abbf7da6f51cd": "Decision Materials",
            "5df79dd77b5abbf7da6f51ce": "Amendment Information",
            "5df79dd77b5abbf7da6f51cf": "Amendment Package",
            "5df79dd77b5abbf7da6f51d0": "Other",
            "5dfc209bc596f00eb48b2b8e": "Presentation",
            "5dfc209bc596f00eb48b2b8f": "Meeting Notes",
            "5dfc209bc596f00eb48b2b90": "Process Order Materials",
        }
        # Group by Act year
        act_2002_ids = {
            "5cf00c03a266b7e1877504ca", "5cf00c03a266b7e1877504cb", "5cf00c03a266b7e1877504cc", "5cf00c03a266b7e1877504cd",
            "5cf00c03a266b7e1877504ce", "5cf00c03a266b7e1877504cf", "5cf00c03a266b7e1877504d0", "5cf00c03a266b7e1877504d1",
            "5cf00c03a266b7e1877504d2", "5cf00c03a266b7e1877504d3", "5cf00c03a266b7e1877504d4", "5cf00c03a266b7e1877504d5",
            "5cf00c03a266b7e1877504d6", "5cf00c03a266b7e1877504d7", "5cf00c03a266b7e1877504d9", "5cf00c03a266b7e1877504da",
            "5d0d212c7d50161b92a80ee3", "5d0d212c7d50161b92a80ee4", "5d0d212c7d50161b92a80ee5", "5d0d212c7d50161b92a80ee6"
        }
        act_2018_ids = set(document_type_lookup.keys()) - act_2002_ids
        mappings = {
            "2002 Act Terms": {k: v for k, v in document_type_lookup.items() if k in act_2002_ids},
            "2018 Act Terms": {k: v for k, v in document_type_lookup.items() if k in act_2018_ids}
        }
        return {"result": {"document_type_mappings": mappings}}
    """Service class for handling statistics and processing info operations."""

    @classmethod
    def get_processing_stats(cls, project_ids=None):
        """Get processing statistics for all projects or filtered by project IDs.
        Args:
            project_ids (list, optional): List of project IDs to filter by.
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
        stats = VectorSearchClient.get_processing_stats(project_ids)
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
