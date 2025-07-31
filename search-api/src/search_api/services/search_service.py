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
    def get_documents_by_query(cls, query, project_ids=None, document_type_ids=None, inference=None, ranking=None, search_strategy=None):
        """Process a user query to retrieve and synthesize relevant information.
        
        This method orchestrates the complete search flow:
        1. Initializes performance metrics
        2. Retrieves relevant documents via vector search with optional filtering
        3. Processes documents through LLM for synthesis
        4. Formats and returns the final response
        
        Args:
            query (str): The user's search query
            project_ids (list, optional): Optional list of project IDs to filter search results by.
                                        If not provided, searches across all projects.
            document_type_ids (list, optional): Optional list of document type IDs to filter search results by.
                                               If not provided, searches across all document types.
            inference (list, optional): Optional list of inference types to enable 
                                       (e.g., ["PROJECT", "DOCUMENTTYPE"]). If not provided,
                                       uses the vector search API's default inference settings.
            ranking (dict, optional): Optional ranking configuration with keys like 'minScore' and 'topN'.
                                     If not provided, uses the vector search API's default ranking settings.
            search_strategy (str, optional): Optional search strategy to use (e.g., "HYBRID_SEMANTIC_FALLBACK",
                                            "HYBRID_PARALLEL", "SEMANTIC_ONLY", etc.). If not provided,
                                            uses the vector search API's default strategy.
            
        Returns:
            dict: A dictionary containing:
                - response (str): LLM-generated answer
                - documents OR document_chunks (list): Relevant documents/chunks used for the answer
                  (key depends on vector search response type)
                - metrics (dict): Performance metrics for the operation including search metadata,
                  detailed search_breakdown with timing, filtering, and strategy information,
                  plus query processing details (original_query, final_semantic_query, etc.)
                - search_quality (str): Quality assessment from vector search API
                - project_inference (dict): Project inference results and metadata
                - document_type_inference (dict): Document type inference results and metadata
                
        Note:
            The response will contain either 'documents' (metadata-focused) or 'document_chunks' 
            (content-focused) depending on what the vector search API returns.
            All parameters except 'query' are optional and maintain backward compatibility.
        """
        current_app.logger.info("=== SearchService.get_documents_by_query started ===")
        current_app.logger.info(f"Query: {query[:200] if query else None}{'...' if query and len(query) > 200 else ''}")
        current_app.logger.info(f"Project IDs: {project_ids}")
        current_app.logger.info(f"Document Type IDs: {document_type_ids}")
        current_app.logger.info(f"Inference: {inference}")
        current_app.logger.info(f"Ranking: {ranking}")
        current_app.logger.info(f"Search Strategy: {search_strategy}")
        
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Get the synthesizer
        current_app.logger.info("Getting LLM synthesizer...")
        get_synthesizer_time = time.time()
        synthesizer = get_synthesizer()
        metrics["get_synthesizer_time"] = round((time.time() - get_synthesizer_time) * 1000, 2)
        current_app.logger.info(f"Synthesizer obtained in {metrics['get_synthesizer_time']}ms")
        
        # Add LLM provider and model information
        metrics["llm_provider"] = os.getenv("LLM_PROVIDER", "ollama")
        if metrics["llm_provider"] == "openai":
            metrics["llm_model"] = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        else:
            metrics["llm_model"] = os.getenv("LLM_MODEL", "")
        
        current_app.logger.info(f"LLM Configuration - Provider: {metrics['llm_provider']}, Model: {metrics['llm_model']}")
 
        # Perform the vector DB search by calling the vector search api
        current_app.logger.info("Starting vector search...")
        search_start = time.time()
        documents_or_chunks, vector_api_response = VectorSearchClient.search(
            query, project_ids, document_type_ids, inference, ranking, search_strategy
        )
        search_duration = round((time.time() - search_start) * 1000, 2)
        current_app.logger.info(f"Vector search completed in {search_duration}ms")
        
        # Extract data from the complete vector API response
        vector_search_data = vector_api_response.get("vector_search", {})
        search_metrics = vector_search_data.get("search_metrics", {})
        search_quality = vector_search_data.get("search_quality", "unknown")
        project_inference = vector_search_data.get("project_inference", {})
        document_type_inference = vector_search_data.get("document_type_inference", {})
        
        # Extract additional vector search metadata
        original_query = vector_search_data.get("original_query", "")
        final_semantic_query = vector_search_data.get("final_semantic_query", "")
        semantic_cleaning_applied = vector_search_data.get("semantic_cleaning_applied", False)
        search_mode = vector_search_data.get("search_mode", "unknown")
        query_processed = vector_search_data.get("query_processed", False)
        inference_settings = vector_search_data.get("inference_settings", {})
        
        # Extract search_breakdown from metrics if available
        api_metrics = vector_api_response.get("metrics", {})
        search_breakdown = api_metrics.get("search_breakdown", {})
        
        # Determine the response type
        response_type = "documents" if "documents" in vector_search_data else "document_chunks"
        documents_key = "documents" if response_type == "documents" else "document_chunks"
        
        # Add all search metrics regardless of whether documents were found
        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        metrics["search_breakdown"] = search_breakdown if search_breakdown else search_metrics  # Include detailed search breakdown metrics
        metrics["search_quality"] = search_quality # Add quality metrics from vector search API
        metrics["original_query"] = original_query # Original user query before processing
        metrics["final_semantic_query"] = final_semantic_query # Final processed query for semantic search
        metrics["semantic_cleaning_applied"] = semantic_cleaning_applied # Whether query cleaning was applied
        metrics["search_mode"] = search_mode # Search mode used by vector search
        metrics["query_processed"] = query_processed # Whether query underwent processing
        metrics["inference_settings"] = inference_settings # Inference configuration details
        
        if not documents_or_chunks:
            return {
                "result": {
                    "response": "No relevant information found.", 
                    documents_key: [], 
                    "metrics": metrics,
                    "search_quality": search_quality,
                    "project_inference": project_inference,
                    "document_type_inference": document_type_inference
                }
            }

        # Prep and query the LLM
        llm_start = time.time()
        current_app.logger.info(f"Calling LLM synthesizer for query: {query}")
        current_app.logger.info(f"Number of documents/chunks for LLM context: {len(documents_or_chunks) if documents_or_chunks else 0}")
        
        try:
            current_app.logger.info("Formatting documents for LLM context...")
            formatted_documents = synthesizer.format_documents_for_context(documents_or_chunks)
            current_app.logger.info(f"Formatted documents for context, length: {len(str(formatted_documents)) if formatted_documents else 0} characters")
            
            current_app.logger.info("Creating LLM prompt...")
            llm_prompt = synthesizer.create_prompt(query, formatted_documents)
            current_app.logger.info(f"LLM prompt created, length: {len(str(llm_prompt)) if llm_prompt else 0} characters")
            
            current_app.logger.info("Querying LLM...")
            llm_response = synthesizer.query_llm(llm_prompt)
            current_app.logger.info(f"LLM response received, length: {len(str(llm_response)) if llm_response else 0} characters")
            
            current_app.logger.info("Formatting LLM response...")
            response = synthesizer.format_llm_response(documents_or_chunks, llm_response)
            
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            current_app.logger.info(f"LLM processing completed in {metrics['llm_time_ms']}ms")
            
        except Exception as e:
            # Log the error
            current_app.logger.error(f"LLM error: {str(e)}")
            current_app.logger.error(f"LLM error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"LLM error traceback: {traceback.format_exc()}")
            
            metrics["llm_error"] = str(e)
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            metrics["error_code"] = 429 if "rate limit" in str(e).lower() or "quota" in str(e).lower() else 500
            # Return a graceful error response with documents and metrics
            return {
                "result": {
                    "response": "An error occurred while processing your request with the LLM. Please try again later.",
                    documents_key: documents_or_chunks,
                    "metrics": metrics,
                    "search_quality": search_quality,
                    "project_inference": project_inference,
                    "document_type_inference": document_type_inference
                }
            }

        # Total execution time
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        current_app.logger.info(f"SearchService.get_documents_by_query completed successfully in {metrics['total_time_ms']}ms")
        current_app.logger.info(f"Vector search time: {search_duration}ms, LLM time: {metrics.get('llm_time_ms', 'N/A')}ms")
        current_app.logger.info(f"Search quality: {search_quality}")
        current_app.logger.info("=== SearchService.get_documents_by_query completed ===")

        return {
            "result": {
                "response": response["response"],
                documents_key: response["documents"],
                "metrics": metrics,
                "search_quality": search_quality,
                "project_inference": project_inference,
                "document_type_inference": document_type_inference
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
        current_app.logger.info("=== SearchService.get_similar_documents started ===")
        current_app.logger.info(f"Document ID: {document_id}")
        current_app.logger.info(f"Project IDs: {project_ids}")
        current_app.logger.info(f"Limit: {limit}")
        
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Call vector search API for similar documents
        current_app.logger.info("Calling VectorSearchClient.find_similar_documents...")
        search_start = time.time()
        source_document_id, documents, search_metrics = VectorSearchClient.find_similar_documents(
            document_id, project_ids, limit
        )
        
        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        current_app.logger.info(f"Similar documents search completed in {metrics['search_time_ms']}ms")
        current_app.logger.info(f"Found {len(documents) if documents else 0} similar documents")
        
        metrics["search_breakdown"] = search_metrics
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        current_app.logger.info(f"SearchService.get_similar_documents completed in {metrics['total_time_ms']}ms")
        current_app.logger.info("=== SearchService.get_similar_documents completed ===")

        return {
            "result": {
                "source_document_id": source_document_id,
                "documents": documents,
                "metrics": metrics
            }
        }
