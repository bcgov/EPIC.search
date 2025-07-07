"""Service for managing search operations and coordinating between vector search and LLM components.

This service handles the core search functionality, including:
- Calling the external vector search API
- Coordinating with the LLM synthesizer
- Collecting performance metrics
- Managing error handling and responses
"""

import os
import time
from datetime import datetime, timezone

from flask import current_app
from .synthesizer_resolver import get_synthesizer
from .vector_search_client import VectorSearchClient


class SearchService:
    """Service class for handling search operations.
    
    This class coordinates the interaction between vector search and LLM components,
    manages performance metrics collection, and handles the overall search flow.
    """

    @classmethod
    def get_documents_by_query(cls, query, project_ids=None):
        """Process a user query to retrieve and synthesize relevant information.
        
        This method orchestrates the complete search flow:
        1. Initializes performance metrics
        2. Retrieves relevant documents via vector search
        3. Processes documents through LLM for synthesis
        4. Formats and returns the final response
        
        Args:
            query (str): The user's search query
            project_ids (list, optional): List of project IDs to filter by
            
        Returns:
            dict: A dictionary containing:
                - response (str): LLM-generated answer
                - documents (list): Relevant documents used for the answer
                - metrics (dict): Performance metrics for the operation
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Get the synthesizer
        get_synthesizer_time = time.time()
        synthesizer = get_synthesizer()
        metrics["get_synthesizer_time"] = round((time.time() - get_synthesizer_time) * 1000, 2)
        
        # Add LLM provider and model information
        metrics["llm_provider"] = os.getenv("LLM_PROVIDER", "ollama")
        if metrics["llm_provider"] == "openai":
            metrics["llm_model"] = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        else:
            metrics["llm_model"] = os.getenv("LLM_MODEL", "")
 
        # Perform the vector DB search by calling the vector search api
        search_start = time.time()
        documents, search_metrics, quality, project_inference = VectorSearchClient.search(query, project_ids)
        
        if not documents:
            return {"result": {"response": "No relevant information found.", "documents": [], "metrics": metrics}}  

        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        metrics["search_breakdown"] = search_metrics  # Include detailed metrics
        metrics["quality"] = quality # Add quality metrics from vector search API
        metrics["project_inference"] = project_inference # Add project inference info

        # Prep and query the LLM
        llm_start = time.time()
        current_app.logger.info(f"Calling LLM synthesizer for query: {query}")
        try:
            formatted_documents = synthesizer.format_documents_for_context(documents)
            llm_prompt = synthesizer.create_prompt(query, formatted_documents)
            llm_response = synthesizer.query_llm(llm_prompt)
            response = synthesizer.format_llm_response(documents, llm_response)
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
        except Exception as e:
            # Log the error
            current_app.logger.error(f"LLM error: {str(e)}")
            metrics["llm_error"] = str(e)
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            metrics["error_code"] = 429 if "rate limit" in str(e).lower() or "quota" in str(e).lower() else 500
            # Return a graceful error response with documents and metrics
            return {
                "result": {
                    "response": "An error occurred while processing your request with the LLM. Please try again later.",
                    "documents": documents,
                    "metrics": metrics,
                    "quality": quality
                }
            }

        # Total execution time
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return {
            "result": {
                "response": response["response"],
                "documents": response["documents"],
                "metrics": metrics,
                "quality": quality,
                "project_inference": project_inference
            }
        }

    @classmethod
    def get_similar_documents(cls, document_id, project_ids=None, limit=10):
        """Find documents similar to a given document.
        
        Args:
            document_id (str): The ID of the document to find similarities for
            project_ids (list, optional): List of project IDs to filter by
            limit (int): Maximum number of similar documents to return
            
        Returns:
            dict: A dictionary containing:
                - source_document_id (str): The ID of the source document
                - documents (list): Similar documents with similarity scores
                - metrics (dict): Performance metrics
        """
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Call vector search API for similar documents
        search_start = time.time()
        source_document_id, documents, search_metrics = VectorSearchClient.find_similar_documents(
            document_id, project_ids, limit
        )
        
        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        metrics["search_breakdown"] = search_metrics
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return {
            "result": {
                "source_document_id": source_document_id,
                "documents": documents,
                "metrics": metrics
            }
        }
