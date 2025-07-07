"""Client for interacting with the external vector search API.

This module provides functionality to call the vector search service
and retrieve relevant documents based on user queries.
"""

import os
import requests
from flask import current_app


class VectorSearchClient:
    """Client for communicating with the external vector search API."""

    @staticmethod
    def search(query, project_ids=None):
        """Call the external vector search API to retrieve relevant documents.
        
        Args:
            query (str): The search query to send to the vector search service
            project_ids (list, optional): List of project IDs to filter by
            
        Returns:
            tuple: A tuple containing:
                - list: Retrieved documents matching the query
                - dict: Search performance metrics
                - dict: Quality metrics from the vector search API
                - dict: Project inference information
                
        Note:
            Returns empty results ([], {}, "unknown", {}) if the API call fails
        """
        try:
            vector_search_url = os.getenv(
                "VECTOR_SEARCH_API_URL", "http://localhost:8080/api/vector-search"
            )
            
            payload = {"query": query}
            if project_ids:
                payload["projectIds"] = project_ids
                
            current_app.logger.info(
                f"Calling vector search API at address: {vector_search_url}"
            )
            response = requests.post(
                vector_search_url, json=payload, timeout=300
            )
            response.raise_for_status()

            api_response = response.json()
            documents = api_response["vector_search"]["documents"]
            metrics = api_response["vector_search"]["search_metrics"]
            quality = api_response["vector_search"]["search_quality"]
            project_inference = api_response["vector_search"].get("project_inference", {})

            return documents, metrics, quality, project_inference
        except Exception as e:
            # Log the error
            current_app.logger.error(f"Error calling vector search API: {str(e)}")
            # Return empty results
            return [], {}, "unknown", {}

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
            base_url = os.getenv("VECTOR_SEARCH_API_URL", "http://localhost:8080/api/vector-search")
            vector_search_url = f"{base_url}/similar"
            
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