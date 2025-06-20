"""Service for managing search operations and coordinating between vector search and LLM components.

This service handles the core search functionality, including:
- Calling the external vector search API
- Coordinating with the LLM synthesizer
- Collecting performance metrics
- Managing error handling and responses
"""

import os
import time
import requests
from datetime import datetime, timezone

from flask import current_app
from .synthesizer_resolver import get_synthesizer


class SearchService:
    """Service class for handling search operations.
    
    This class coordinates the interaction between vector search and LLM components,
    manages performance metrics collection, and handles the overall search flow.
    """

    @classmethod
    def call_vector_search_api(cls, query):
        """Call the external vector search API to retrieve relevant documents.
        
        Args:
            query (str): The search query to send to the vector search service
            
        Returns:
            tuple: A tuple containing:
                - list: Retrieved documents matching the query
                - dict: Search performance metrics
                
        Note:
            Returns empty results ([], {}) if the API call fails
        """
        try:
            vector_search_url = os.getenv(
                "VECTOR_SEARCH_API_URL", "http://localhost:3300/api/vector-search"
            )
            current_app.logger.info(
                f"Calling vector search API at address: {vector_search_url}"
            )
            response = requests.post(
                vector_search_url, json={"query": query}, timeout=300
            )
            response.raise_for_status()

            api_response = response.json()
            documents = api_response["vector_search"]["documents"]
            metrics = api_response["vector_search"]["search_metrics"]

            return documents, metrics
        except Exception as e:
            # Log the error
            current_app.logger.error(f"Error calling vector search API: {str(e)}")
            # Return empty results
            return [], {}

    @classmethod
    def get_documents_by_query(cls, query):
        """Process a user query to retrieve and synthesize relevant information.
        
        This method orchestrates the complete search flow:
        1. Initializes performance metrics
        2. Retrieves relevant documents via vector search
        3. Processes documents through LLM for synthesis
        4. Formats and returns the final response
        
        Args:
            query (str): The user's search query
            
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
        documents, search_metrics = cls.call_vector_search_api(query)
        
        if not documents:
            return {"result": {"response": "No relevant information found.", "documents": [], "metrics": metrics}}  

        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        metrics["search_breakdown"] = search_metrics  # Include detailed metrics

        # Prep and query the LLM
        llm_start = time.time()
        formatted_documents = synthesizer.format_documents_for_context(documents)
        llm_prompt = synthesizer.create_prompt(query, formatted_documents)
        llm_response = synthesizer.query_llm(llm_prompt)
        response = synthesizer.format_llm_response(documents, llm_response)
        metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)

        # Total execution time
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return {
            "result": {
                "response": response["response"],
                "documents": response["documents"],
                "metrics": metrics,
            }
        }
