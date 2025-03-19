"""Service for search management."""

import os
import time
import requests

from flask import current_app
from .synthesizer_resolver import get_synthesizer
from .vector_search import search


class SearchService:
    """Search management service."""

    @classmethod
    def call_vector_search_api(cls, query):
        """Call the external vector search API."""
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
        """Get documents by user query."""
        metrics = {}
        start_time = time.time()

        # Get the synthesizer
        synthesizer = get_synthesizer()

        # Call pre_query_llm before performing the search
        pre_query_start = time.time()
        pre_query_result = synthesizer.pre_query_llm(query)
        metrics["pre_query_time_ms"] = round((time.time() - pre_query_start) * 1000, 2)

        if not pre_query_result:
            return {
                "result": {
                    "response": "Pre-query check failed. No documents retrieved.",
                    "documents": [],
                    "metrics": metrics,
                }
            }

        # Perform the vector DB search
        search_start = time.time()
        documents, search_metrics = cls.call_vector_search_api(
            query
        )  # call the vector search API
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
