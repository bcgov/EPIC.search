"""Client for interacting with the external vector search API.

This module provides comprehensive functionality to call the vector search service
and supports all MCP (Model Context Protocol) tool endpoints for agentic workflows.

The client is organized into logical groups:
- Search Operations: Core search functionality with various strategies
- Discovery Operations: Metadata and capability discovery
- Intelligence Operations: AI-powered recommendations and filtering
- Statistics Operations: Processing metrics and health monitoring

All endpoints support the MCP server integration for intelligent orchestration
while maintaining direct API access for traditional workflows.
"""

import os
import requests
from flask import current_app
from typing import List, Dict, Any, Optional


class VectorSearchClient:
    """Client for communicating with the external vector search API.
    
    Supports all 16 MCP tools for comprehensive agentic workflow integration.
    """

    # =============================================================================
    # SEARCH OPERATIONS - Core search functionality (5 methods)
    # =============================================================================

    @staticmethod
    def search(query, project_ids=None, document_type_ids=None, inference=None, ranking=None, search_strategy=None):
        """Advanced two-stage hybrid search with comprehensive parameters.
        
        MCP Tool: vector_search
        Endpoint: POST /vector-search
        
        Args:
            query (str): The search query to send to the vector search service
            project_ids (list, optional): Optional list of project IDs to filter search results by
            document_type_ids (list, optional): Optional list of document type IDs to filter search results by
            inference (list, optional): Optional list of inference types to enable (e.g., ["PROJECT", "DOCUMENTTYPE"])
            ranking (dict, optional): Optional ranking configuration with keys like 'minScore' and 'topN'
            search_strategy (str, optional): Optional search strategy:
                - "HYBRID_SEMANTIC_FALLBACK" (default)
                - "HYBRID_KEYWORD_FALLBACK" 
                - "SEMANTIC_ONLY"
                - "KEYWORD_ONLY"
                - "HYBRID_PARALLEL"
            
        Returns:
            tuple: (documents_or_chunks, complete_api_response)
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/vector-search"
            payload = {"query": query}
            
            # Add optional parameters if provided - maintains backward compatibility
            if project_ids:
                payload["projectIds"] = project_ids
            if document_type_ids:
                payload["documentTypeIds"] = document_type_ids
            if inference:
                payload["inference"] = inference
            if ranking:
                payload["ranking"] = ranking
            if search_strategy:
                payload["searchStrategy"] = search_strategy
                
            current_app.logger.info(f"Calling vector search API at address: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()

            api_response = response.json()
            vector_search_data = api_response["vector_search"]
            
            # Handle both response types: documents or document_chunks
            documents_or_chunks = vector_search_data.get("documents") or vector_search_data.get("document_chunks", [])

            return documents_or_chunks, api_response
        except Exception as e:
            current_app.logger.error(f"Error calling vector search API: {str(e)}")
            return [], {}

    @staticmethod
    def find_similar_documents(document_id, project_ids=None, limit=10):
        """Legacy document similarity endpoint.
        
        MCP Tool: find_similar_documents
        Endpoint: POST /vector-search/similar
        
        Args:
            document_id (str): The ID of the document to find similarities for
            project_ids (list, optional): List of project IDs to filter by
            limit (int): Maximum number of similar documents to return (default: 10)
            
        Returns:
            tuple: (source_document_id, similar_documents, metrics)
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/vector-search/similar"
            
            payload = {
                "documentId": document_id,
                "limit": limit
            }
            if project_ids:
                payload["projectIds"] = project_ids
                
            current_app.logger.info(f"Calling vector search similar API at: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()

            api_response = response.json()
            similarity_data = api_response["document_similarity"]
            
            source_document_id = similarity_data["source_document_id"]
            documents = similarity_data["documents"]
            metrics = similarity_data["search_metrics"]

            return source_document_id, documents, metrics
        except Exception as e:
            current_app.logger.error(f"Error calling vector search similar API: {str(e)}")
            return "", [], {}

    @staticmethod
    def search_with_auto_inference(query, context=None, confidence_threshold=0.5, max_results=10):
        """Smart search with automatic project and document type inference.
        
        MCP Tool: search_with_auto_inference
        Endpoint: POST /inference-search
        
        Args:
            query (str): Search query - system will intelligently determine relevant projects and document types
            context (str, optional): Additional context about what the user is looking for
            confidence_threshold (float): Confidence threshold for automatic filtering (0.0-1.0)
            max_results (int): Maximum number of results to return
            
        Returns:
            dict: Search results with inferred filters and confidence scores
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/inference-search"
            
            payload = {
                "query": query,
                "confidence_threshold": confidence_threshold,
                "max_results": max_results
            }
            if context:
                payload["context"] = context
                
            current_app.logger.info(f"Calling vector search inference API at: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search inference API: {str(e)}")
            return {}

    @staticmethod
    def document_similarity_search(document_id, project_ids=None, limit=10):
        """Document-level embedding similarity search.
        
        MCP Tool: document_similarity_search
        Endpoint: POST /document-similarity
        
        Args:
            document_id (str): The document ID to find similar documents for
            project_ids (list, optional): Optional list of project IDs to filter similar documents by
            limit (int): Maximum number of similar documents to return
            
        Returns:
            dict: Similar documents with document-level embeddings
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/document-similarity"
            
            payload = {
                "document_id": document_id,
                "limit": limit
            }
            if project_ids:
                payload["project_ids"] = project_ids
                
            current_app.logger.info(f"Calling vector search document similarity API at: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search document similarity API: {str(e)}")
            return {}

    @staticmethod
    def agentic_search(query, context=None, user_intent=None, max_results=15, include_stats=False):
        """Multi-strategy intelligent search orchestration.
        
        MCP Tool: agentic_search
        Endpoint: POST /agentic-search
        
        Args:
            query (str): Natural language search query from the user
            context (str, optional): Additional context about what the user is looking for
            user_intent (str, optional): Detected user intent: find_documents, find_similar, explore_topic, get_overview, specific_lookup
            max_results (int): Maximum number of results to return
            include_stats (bool): Whether to include processing statistics in the response
            
        Returns:
            dict: Comprehensive search results from multiple strategies
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/agentic-search"
            
            payload = {
                "query": query,
                "max_results": max_results,
                "include_stats": include_stats
            }
            if context:
                payload["context"] = context
            if user_intent:
                payload["user_intent"] = user_intent
                
            current_app.logger.info(f"Calling vector search agentic API at: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search agentic API: {str(e)}")
            return {}

    # =============================================================================
    # DISCOVERY OPERATIONS - Metadata and capability discovery (6 methods)
    # =============================================================================

    @staticmethod
    def get_projects_list():
        """Get list of available projects for filtering.
        
        MCP Tool: get_available_projects
        Endpoint: GET /tools/projects
        
        Returns:
            list: Array of project objects with project_id and project_name
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/tools/projects"
            
            current_app.logger.info(f"Calling vector search projects list API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            data = response.json()
            return data.get('projects', [])
        except Exception as e:
            current_app.logger.error(f"Error calling vector search projects list API: {str(e)}")
            return []

    @staticmethod
    def get_document_types():
        """Get document types with aliases and descriptions.
        
        MCP Tool: get_available_document_types
        Endpoint: GET /tools/document-types
        
        Returns:
            dict: Document types with metadata and aliases
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/tools/document-types"
            
            current_app.logger.info(f"Calling vector search document types API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search document types API: {str(e)}")
            return {}

    @staticmethod
    def get_document_type_details(type_id):
        """Get detailed information for a specific document type.
        
        MCP Tool: get_document_type_details
        Endpoint: GET /tools/document-types/{type_id}
        
        Args:
            type_id (str): The document type ID to get details for
            
        Returns:
            dict: Document type details with id, name, and aliases
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/tools/document-types/{type_id}"
            
            current_app.logger.info(f"Calling vector search document type details API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search document type details API: {str(e)}")
            return {}

    @staticmethod
    def get_search_strategies():
        """Get available search strategies and capabilities.
        
        MCP Tool: get_search_strategies
        Endpoint: GET /search-strategies
        
        Returns:
            dict: Available search strategies with descriptions and capabilities
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/search-strategies"
            
            current_app.logger.info(f"Calling vector search strategies API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search strategies API: {str(e)}")
            return {}

    @staticmethod
    def get_inference_options():
        """Get available ML inference services and options.
        
        MCP Tool: get_inference_options
        Endpoint: GET /inference-options
        
        Returns:
            dict: Available inference services with capabilities
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/inference-options"
            
            current_app.logger.info(f"Calling vector search inference options API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search inference options API: {str(e)}")
            return {}

    @staticmethod
    def get_api_capabilities():
        """Complete API metadata discovery for adaptive clients.
        
        MCP Tool: get_api_capabilities
        Endpoint: GET /capabilities
        
        Returns:
            dict: Complete API metadata and endpoint discovery
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/capabilities"
            
            current_app.logger.info(f"Calling vector search capabilities API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search capabilities API: {str(e)}")
            return {}

    # =============================================================================
    # INTELLIGENCE OPERATIONS - AI-powered recommendations (1 method)
    # =============================================================================

    @staticmethod
    def suggest_filters(query, context=None, confidence_threshold=0.6):
        """AI-powered filter recommendations based on query analysis.
        
        MCP Tool: suggest_filters
        Endpoint: POST /suggest-filters
        
        Args:
            query (str): The user's search query to analyze for filter suggestions
            context (str, optional): Additional context about what the user is looking for
            confidence_threshold (float): Minimum confidence level for filter suggestions
            
        Returns:
            dict: Recommended filters with confidence scores
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/suggest-filters"
            
            payload = {
                "query": query,
                "confidence_threshold": confidence_threshold
            }
            if context:
                payload["context"] = context
                
            current_app.logger.info(f"Calling vector search suggest filters API at: {vector_search_url}")
            response = requests.post(vector_search_url, json=payload, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search suggest filters API: {str(e)}")
            return {}

    # =============================================================================
    # STATISTICS OPERATIONS - Processing metrics and health monitoring (4 methods)
    # =============================================================================

    @staticmethod
    def get_processing_stats(project_ids=None):
        """Get processing statistics for projects.
        
        MCP Tool: get_processing_stats
        Endpoint: GET /stats/processing
        
        Args:
            project_ids (list, optional): List of project IDs to filter by (Note: filtering now handled by vector API internally)
            
        Returns:
            dict: Processing statistics with per-project and aggregate metrics
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/stats/processing"
            
            current_app.logger.info(f"Calling vector search processing stats API (GET) at: {vector_search_url}")
            if project_ids:
                current_app.logger.info(f"Note: project_ids filter ({project_ids}) ignored - vector API handles filtering internally")
            
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search processing stats API: {str(e)}")
            return {}

    @staticmethod
    def get_project_details(project_id):
        """Get detailed processing information for a specific project.
        
        MCP Tool: get_project_details
        Endpoint: GET /stats/processing/{project_id}
        
        Args:
            project_id (str): The project ID to get details for
            
        Returns:
            dict: Detailed project processing logs and metrics
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/stats/processing/{project_id}"
            
            current_app.logger.info(f"Calling vector search project details API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search project details API: {str(e)}")
            return {}

    @staticmethod
    def get_system_summary():
        """Get high-level system overview and health status.
        
        MCP Tool: get_system_summary
        Endpoint: GET /stats/summary
        
        Returns:
            dict: High-level system metrics and health status
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/stats/summary"
            
            current_app.logger.info(f"Calling vector search system summary API at: {vector_search_url}")
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search system summary API: {str(e)}")
            return {}

    @staticmethod
    def analyze_project_health(project_ids=None, health_threshold=90):
        """Intelligent analysis of project processing health.
        
        MCP Tool: analyze_project_health
        Endpoint: GET /stats/health or GET /stats/health/{project_id}
        
        Args:
            project_ids (list, optional): List of project IDs to analyze
            health_threshold (float): Success rate threshold below which a project is considered unhealthy
            
        Returns:
            dict: Project health analysis with recommendations
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            
            if project_ids and len(project_ids) == 1:
                # Single project health check
                vector_search_url = f"{base_url}/stats/health/{project_ids[0]}"
                params = {"health_threshold": health_threshold}
            else:
                # Multiple projects or all projects health check
                vector_search_url = f"{base_url}/stats/health"
                params = {"health_threshold": health_threshold}
                if project_ids:
                    params["project_ids"] = ",".join(project_ids)
            
            current_app.logger.info(f"Calling vector search project health API at: {vector_search_url}")
            response = requests.get(vector_search_url, params=params, timeout=300)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Error calling vector search project health API: {str(e)}")
            return {}

    # =============================================================================
    # MCP SUPPORT UTILITIES
    # =============================================================================

    @staticmethod
    def get_supported_mcp_tools():
        """Get list of all supported MCP tools and their corresponding methods.
        
        Returns:
            dict: Mapping of MCP tool names to client methods and endpoints
        """
        return {
            # Search Operations
            "vector_search": {
                "method": "search",
                "endpoint": "POST /vector-search",
                "description": "Advanced two-stage hybrid search with comprehensive parameters"
            },
            "find_similar_documents": {
                "method": "find_similar_documents", 
                "endpoint": "POST /vector-search/similar",
                "description": "Legacy document similarity endpoint"
            },
            "search_with_auto_inference": {
                "method": "search_with_auto_inference",
                "endpoint": "POST /inference-search", 
                "description": "Smart search with automatic project and document type inference"
            },
            "document_similarity_search": {
                "method": "document_similarity_search",
                "endpoint": "POST /document-similarity",
                "description": "Document-level embedding similarity search"
            },
            "agentic_search": {
                "method": "agentic_search",
                "endpoint": "POST /agentic-search",
                "description": "Multi-strategy intelligent search orchestration"
            },
            
            # Discovery Operations
            "get_available_projects": {
                "method": "get_projects_list",
                "endpoint": "GET /tools/projects",
                "description": "Get list of available projects for filtering"
            },
            "get_available_document_types": {
                "method": "get_document_types",
                "endpoint": "GET /tools/document-types",
                "description": "Get document types with aliases and descriptions"
            },
            "get_document_type_details": {
                "method": "get_document_type_details",
                "endpoint": "GET /tools/document-types/{type_id}",
                "description": "Get detailed information for a specific document type"
            },
            "get_search_strategies": {
                "method": "get_search_strategies",
                "endpoint": "GET /search-strategies",
                "description": "Get available search strategies and capabilities"
            },
            "get_inference_options": {
                "method": "get_inference_options",
                "endpoint": "GET /inference-options",
                "description": "Get available ML inference services and options"
            },
            "get_api_capabilities": {
                "method": "get_api_capabilities",
                "endpoint": "GET /capabilities",
                "description": "Complete API metadata discovery for adaptive clients"
            },
            
            # Intelligence Operations
            "suggest_filters": {
                "method": "suggest_filters",
                "endpoint": "POST /suggest-filters",
                "description": "AI-powered filter recommendations based on query analysis"
            },
            
            # Statistics Operations
            "get_processing_stats": {
                "method": "get_processing_stats",
                "endpoint": "GET|POST /stats/processing",
                "description": "Get processing statistics for projects"
            },
            "get_project_details": {
                "method": "get_project_details",
                "endpoint": "GET /stats/processing/{project_id}",
                "description": "Get detailed processing information for a specific project"
            },
            "get_system_summary": {
                "method": "get_system_summary",
                "endpoint": "GET /stats/summary",
                "description": "Get high-level system overview and health status"
            },
            "analyze_project_health": {
                "method": "analyze_project_health",
                "endpoint": "GET /stats/health[/{project_id}]",
                "description": "Intelligent analysis of project processing health"
            }
        }
