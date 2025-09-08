"""Service for managing statistics and processing information from the vector search API.

This service provides methods to retrieve system-wide, per-project, and filtered processing statistics
by wrapping the VectorSearchClient stats endpoints. Also provides access to projects and document types.
"""

import time
from datetime import datetime, timezone
from flask import current_app
from search_api.clients.vector_search_client import VectorSearchClient
from ..utils.cache import cache_with_ttl

class StatsService:
    """Service class for handling statistics, projects, and document type operations."""

    @classmethod
    @cache_with_ttl(ttl_seconds=3600)  # Cache for 1 hour
    def get_document_type_mappings(cls):
        """Get document type mappings from the vector API with caching.
        
        Returns:
            dict: Response containing:
                - result.document_types: All document types with names and aliases from the vector API
                - result.grouped_by_act: Legacy grouped format for backward compatibility
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get document types from vector API
        document_types_response = VectorSearchClient.get_document_types()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if document_types_response and "document_types" in document_types_response:
            document_types = document_types_response["document_types"]
            
            # Create legacy grouped format using the 'act' field from the response
            legacy_mappings = {
                "2002 Act Terms": {},
                "2018 Act Terms": {}
            }
            
            for type_id, type_info in document_types.items():
                act_key = "2002 Act Terms" if type_info.get("act") == "2002_act_terms" else "2018 Act Terms"
                legacy_mappings[act_key][type_id] = type_info["name"]
            
            result = {
                "document_types": document_types,  # Full data with aliases
                "grouped_by_act": legacy_mappings,  # Legacy format
                "total_types": len(document_types),
                "act_2002_count": len(legacy_mappings["2002 Act Terms"]),
                "act_2018_count": len(legacy_mappings["2018 Act Terms"])
            }
        else:
            # Fallback to empty response if API call fails
            current_app.logger.warning("Failed to get document types from vector API, returning empty response")
            result = {
                "document_types": {},
                "grouped_by_act": {"2002 Act Terms": {}, "2018 Act Terms": {}},
                "total_types": 0,
                "act_2002_count": 0,
                "act_2018_count": 0,
                "error": "Failed to retrieve document types from vector API"
            }
        
        result["metrics"] = metrics
        return {"result": result}

    @classmethod
    @cache_with_ttl(ttl_seconds=1800)  # Cache for 30 minutes
    def get_projects_list(cls):
        """Get lightweight list of all projects with caching.
        
        Returns:
            dict: Response containing:
                - result.projects: Array of projects with project_id and project_name
                - result.total_projects: Count of projects
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get projects from vector API
        projects_array = VectorSearchClient.get_projects_list()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if projects_array:
            result = {
                "projects": projects_array,
                "total_projects": len(projects_array)
            }
        else:
            # Fallback to empty response if API call fails
            current_app.logger.warning("Failed to get projects from vector API, returning empty response")
            result = {
                "projects": [],
                "total_projects": 0,
                "error": "Failed to retrieve projects from vector API"
            }
        
        result["metrics"] = metrics
        return {"result": result}

    @classmethod
    def get_document_type_details(cls, type_id):
        """Get detailed information for a specific document type.
        
        Args:
            type_id (str): The document type ID to get details for
            
        Returns:
            dict: Response containing:
                - result.document_type: Document type details with id, name, and aliases
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get document type details from vector API
        type_response = VectorSearchClient.get_document_type_details(type_id)
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if type_response and "document_type" in type_response:
            result = {"document_type": type_response["document_type"]}
        else:
            # Fallback to empty response if API call fails
            current_app.logger.warning(f"Failed to get document type {type_id} from vector API")
            result = {
                "document_type": None,
                "error": f"Failed to retrieve document type {type_id} from vector API"
            }
        
        result["metrics"] = metrics
        return {"result": result}

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

    @classmethod
    @cache_with_ttl(ttl_seconds=3600)  # Cache for 1 hour
    def get_search_strategies(cls):
        """Get available search strategies from the vector API with caching.
        
        Returns:
            dict: Response containing:
                - result.strategies: List of available search strategies with descriptions
                - result.total_strategies: Count of available strategies
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get search strategies from vector API
        strategies_response = VectorSearchClient.get_search_strategies()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if strategies_response and "search_strategies" in strategies_response:
            # Convert the search_strategies dict to a list format for easier consumption
            strategies_dict = strategies_response["search_strategies"]
            strategies_list = []
            
            for strategy_name, strategy_info in strategies_dict.items():
                strategies_list.append({
                    "name": strategy_name,
                    "description": strategy_info.get("description", ""),
                    "use_cases": strategy_info.get("use_cases", []),
                    "steps": strategy_info.get("steps", []),
                    "performance": strategy_info.get("performance", ""),
                    "accuracy": strategy_info.get("accuracy", "")
                })
            
            result = {
                "strategies": strategies_list,
                "total_strategies": strategies_response.get("total_strategies", len(strategies_list)),
                "default_strategy": strategies_response.get("default_strategy", "HYBRID_SEMANTIC_FALLBACK"),
                "metrics": metrics
            }
            return {"result": result}
        else:
            return {"result": {"strategies": [], "total_strategies": 0, "metrics": metrics}}

    @classmethod
    @cache_with_ttl(ttl_seconds=3600)  # Cache for 1 hour
    def get_inference_options(cls):
        """Get available ML inference options from the vector API with caching.
        
        Returns:
            dict: Response containing:
                - result.inference_options: List of available ML inference options and capabilities
                - result.total_options: Count of available inference options
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get inference options from vector API
        options_response = VectorSearchClient.get_inference_options()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if options_response and "inference_options" in options_response:
            inference_options = options_response["inference_options"]
            
            result = {
                "inference_options": inference_options,
                "total_options": len(inference_options),
                "metrics": metrics
            }
            return {"result": result}
        else:
            return {"result": {"inference_options": [], "total_options": 0, "metrics": metrics}}

    @classmethod
    @cache_with_ttl(ttl_seconds=3600)  # Cache for 1 hour
    def get_api_capabilities(cls):
        """Get complete API metadata and capabilities from the vector API with caching.
        
        Returns:
            dict: Response containing:
                - result.capabilities: Complete API metadata including endpoints, schemas, and features
                - result.endpoints_count: Count of documented endpoints
                - result.metrics: Performance timing data for this API call
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Get API capabilities from vector API
        capabilities_response = VectorSearchClient.get_api_capabilities()
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        if capabilities_response and "capabilities" in capabilities_response:
            capabilities = capabilities_response["capabilities"]
            
            result = {
                "capabilities": capabilities,
                "endpoints_count": len(capabilities.get("endpoints", [])),
                "metrics": metrics
            }
            return {"result": result}
        else:
            # Provide basic fallback capabilities if vector API doesn't support this endpoint
            fallback_capabilities = {
                "api_version": "1.0",
                "name": "Vector Search API",
                "description": "Semantic and keyword search with ML inference",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/vector-search",
                        "description": "Main semantic/keyword search"
                    },
                    {
                        "method": "POST", 
                        "path": "/api/document-similarity",
                        "description": "Find similar documents"
                    },
                    {
                        "method": "GET",
                        "path": "/api/tools/projects",
                        "description": "List all projects"
                    },
                    {
                        "method": "GET",
                        "path": "/api/tools/document-types",
                        "description": "List all document types"
                    },
                    {
                        "method": "GET",
                        "path": "/api/tools/search-strategies",
                        "description": "Get available search strategies"
                    },
                    {
                        "method": "GET",
                        "path": "/api/tools/inference-options",
                        "description": "Get ML inference services"
                    },
                    {
                        "method": "GET",
                        "path": "/api/stats/processing",
                        "description": "All projects processing statistics"
                    },
                    {
                        "method": "GET",
                        "path": "/api/stats/summary",
                        "description": "Overall system summary statistics"
                    }
                ],
                "features": [
                    "semantic_search",
                    "keyword_search", 
                    "hybrid_search",
                    "document_similarity",
                    "project_filtering",
                    "document_type_filtering",
                    "ml_inference"
                ]
            }
            
            result = {
                "capabilities": fallback_capabilities,
                "endpoints_count": len(fallback_capabilities["endpoints"]),
                "metrics": metrics
            }
            return {"result": result}
