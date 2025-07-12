"""Client for interacting with the external vector search API.

This module provides functionality to call the vector search service
and retrieve relevant documents based on user queries, as well as
access processing statistics and system metrics.

The search functionality supports optional filtering by project IDs and document types,
as well as configurable inference settings for enhanced search capabilities.
All optional parameters maintain backward compatibility with existing API clients.
"""

import os
import requests
from flask import current_app


class VectorSearchClient:
    """Client for communicating with the external vector search API."""

    @staticmethod
    def search(query, project_ids=None, document_type_ids=None, inference=None):
        """Call the external vector search API to retrieve relevant documents or document chunks.
        
        Args:
            query (str): The search query to send to the vector search service
            project_ids (list, optional): Optional list of project IDs to filter search results by.
                                        If not provided, searches across all projects.
            document_type_ids (list, optional): Optional list of document type IDs to filter search results by.
                                               If not provided, searches across all document types.
            inference (list, optional): Optional list of inference types to enable 
                                       (e.g., ["PROJECT", "DOCUMENTTYPE"]). If not provided,
                                       uses the vector search API's default inference settings.
            
        Returns:
            tuple: A tuple containing:
                - list: Retrieved documents or document chunks matching the query
                - dict: Search performance metrics
                - str: Search quality assessment  
                - dict: Project inference information (if available and enabled)
                - dict: Document type inference information (if available and enabled)
                - dict: Additional response metadata (search_mode, inference_settings, etc.)
                
        Note:
            Returns empty results ([], {}, "unknown", {}, {}, {}) if the API call fails.
            All parameters except 'query' are optional and maintain backward compatibility.
        """
        try:
            base_url = os.getenv(
                "VECTOR_SEARCH_API_URL", "http://localhost:8080/api"
            )
            
            vector_search_url = f"{base_url}/vector-search"
            payload = {"query": query}
            
            # Add optional parameters if provided - maintains backward compatibility
            if project_ids:
                payload["projectIds"] = project_ids
            if document_type_ids:
                payload["documentTypeIds"] = document_type_ids
            if inference:
                payload["inference"] = inference
                
            current_app.logger.info(
                f"Calling vector search API at address: {vector_search_url}"
            )
            response = requests.post(
                vector_search_url, json=payload, timeout=300
            )
            response.raise_for_status()

            api_response = response.json()
            vector_search_data = api_response["vector_search"]
            
            # Handle both response types: documents or document_chunks
            documents_or_chunks = vector_search_data.get("documents") or vector_search_data.get("document_chunks", [])
            
            search_metrics = vector_search_data.get("search_metrics", {})
            search_quality = vector_search_data.get("search_quality", "unknown")
            
            # Extract inference information (may not be present in all responses)
            project_inference = vector_search_data.get("project_inference", {})
            document_type_inference = vector_search_data.get("document_type_inference", {})
            
            # Extract additional metadata
            additional_metadata = {
                "original_query": vector_search_data.get("original_query"),
                "final_semantic_query": vector_search_data.get("final_semantic_query"),
                "search_mode": vector_search_data.get("search_mode"),
                "query_processed": vector_search_data.get("query_processed"),
                "inference_settings": vector_search_data.get("inference_settings", {}),
                "response_type": "documents" if "documents" in vector_search_data else "document_chunks"
            }

            return documents_or_chunks, search_metrics, search_quality, project_inference, document_type_inference, additional_metadata
        except Exception as e:
            # Log the error
            current_app.logger.error(f"Error calling vector search API: {str(e)}")
            # Return empty results
            return [], {}, "unknown", {}, {}, {}

    @staticmethod
    def find_similar_documents(document_id, project_ids=None, limit=10):
        """Call the external vector search API to find similar documents.
        
        Args:
            document_id (str): The ID of the document to find similarities for
            project_ids (list, optional): List of project IDs to filter by
            limit (int): Maximum number of similar documents to return (default: 10)
            
        Returns:
            tuple: A tuple containing:
                - str: Source document ID
                - list: Similar documents with similarity scores and metadata
                - dict: Search performance metrics
                
        Note:
            Returns empty results ("", [], {}) if the API call fails
        """
        try:
            # Use environment variable for base URL, append /similar endpoint
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/vector-search/similar"
            
            payload = {
                "documentId": document_id,
                "limit": limit
            }
            if project_ids:
                payload["projectIds"] = project_ids
                
            current_app.logger.info(
                f"Calling vector search similar API at: {vector_search_url}"
            )
            response = requests.post(
                vector_search_url, json=payload, timeout=300
            )
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
    def get_processing_stats(project_ids=None):
        """Get processing statistics for projects.
        
        Args:
            project_ids (list, optional): List of project IDs to filter by.
                                        If None, returns stats for all projects.
            
        Returns:
            dict: Processing statistics containing:
                - processing_stats: Statistics data
                - projects: Per-project statistics
                - summary: Aggregate metrics
                
        Note:
            Returns empty dict {} if the API call fails
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            
            if project_ids:
                # POST request with project IDs filter
                vector_search_url = f"{base_url}/stats/processing"
                payload = {"projectIds": project_ids}
                
                current_app.logger.info(
                    f"Calling vector search processing stats API (POST) at: {vector_search_url}"
                )
                response = requests.post(
                    vector_search_url, json=payload, timeout=300
                )
            else:
                # GET request for all projects
                vector_search_url = f"{base_url}/stats/processing"
                
                current_app.logger.info(
                    f"Calling vector search processing stats API (GET) at: {vector_search_url}"
                )
                response = requests.get(vector_search_url, timeout=300)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"Error calling vector search processing stats API: {str(e)}")
            return {}

    @staticmethod
    def get_project_details(project_id):
        """Get detailed processing logs for a specific project.
        
        Args:
            project_id (str): The project ID to get details for
            
        Returns:
            dict: Project details containing:
                - processing_logs: Array of document processing records
                - project_id: The requested project ID
                
        Note:
            Returns empty dict {} if the API call fails
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/stats/project/{project_id}"
            
            current_app.logger.info(
                f"Calling vector search project details API at: {vector_search_url}"
            )
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"Error calling vector search project details API: {str(e)}")
            return {}

    @staticmethod
    def get_system_summary():
        """Get high-level processing summary across the entire system.
        
        Returns:
            dict: System summary containing:
                - summary: High-level aggregate metrics
                - total_projects: Number of projects
                - total_documents: Number of documents processed
                - other system-wide statistics
                
        Note:
            Returns empty dict {} if the API call fails
        """
        try:
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api")
            vector_search_url = f"{base_url}/stats/summary"
            
            current_app.logger.info(
                f"Calling vector search system summary API at: {vector_search_url}"
            )
            response = requests.get(vector_search_url, timeout=300)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            current_app.logger.error(f"Error calling vector search system summary API: {str(e)}")
            return {}