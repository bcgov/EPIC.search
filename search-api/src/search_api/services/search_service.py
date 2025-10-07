"""Service for managing search operations and coordinating between vector search and LLM components.

This service handles the core search functionality, including:
- Calling the external vector search API
- Coordinating with the LLM synthesizer
- Collecting performance metrics
- Managing error handling and responses
"""

import os
import re
import time

from datetime import datetime, timezone
from flask import current_app
from search_api.clients.vector_search_client import VectorSearchClient

class SearchService:
    """Service class for handling search operations.
    
    This class coordinates the interaction between vector search and LLM components,
    manages performance metrics collection, and handles the overall search flow.
    """ 

    @classmethod
    def get_documents_by_query(cls, query, project_ids=None, document_type_ids=None, inference=None, ranking=None, search_strategy=None, mode="rag", user_location=None, location=None, project_status=None, years=None):
        """Process a user query to retrieve and synthesize relevant information.
        
        This method orchestrates the complete search flow:
        1. Initializes performance metrics
        2. [AI/AGENT MODE] Optionally uses LLM to extract project/filter info from natural language
        3. Retrieves relevant documents via vector search with optional filtering
        4. Processes documents through LLM for synthesis
        5. Formats and returns the final response
        
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
            mode (str, optional): Processing mode - "rag" (pure RAG, default), "summary" (RAG + AI summarization),
                                 "ai" (AI processing without agent), or "agent" (full agent processing). 
                                 Controls the level of AI processing applied:
                                 - "rag": Direct vector search with provided parameters
                                 - "summary": Direct vector search + AI summarization (no parameter extraction)
                                 - "ai": LLM parameter extraction and summarization, no agent stub
                                 - "agent": Full AI processing including agent stub for complex queries
            user_location (dict, optional): Optional user location data for location-aware queries.
                                           Should contain location information like latitude, longitude,
                                           city, or region for geographic search enhancement.
            
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
        current_app.logger.info(f"Processing Mode: {mode}")
        current_app.logger.info(f"User Location: {user_location}")
        current_app.logger.info(f"Project Status: {project_status}")
        current_app.logger.info(f"Years: {years}")
        
        # Initialize metrics and timing
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        metrics["processing_mode"] = mode
        
        # Handle auto mode - determine optimal tier based on query complexity
        if mode == "auto":
            current_app.logger.info("🤖 AUTO MODE: Analyzing query to determine optimal processing tier...")
            auto_mode = cls._determine_auto_mode(query, user_location, metrics)
            current_app.logger.info(f"🤖 AUTO MODE: Selected tier '{auto_mode}' for query")
            mode = auto_mode
            metrics["auto_selected_mode"] = auto_mode
        
        # Route to appropriate mode handler - each handler returns complete response
        from search_api.services.search_handlers import RAGHandler, RAGSummaryHandler, AIHandler, AgentHandler
        
        if mode == "agent":
            # Agent mode handles entire query processing internally with fallback to AI mode
            result = AgentHandler.handle(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location, project_status, years)
            
            # Check if agent failed and fallback to AI mode
            if result.get("result", {}).get("error") and result.get("result", {}).get("metrics", {}).get("agent_fallback"):
                current_app.logger.info("🤖 AGENT MODE: Falling back to AI mode due to agent failure...")
                # Reset metrics for AI mode processing
                ai_metrics = result.get("result", {}).get("metrics", {})
                return AIHandler.handle(query, project_ids, document_type_ids, search_strategy, inference, ranking, ai_metrics, user_location, project_status, years)
            
            return result
        elif mode == "ai":
            # AI mode handles LLM parameter extraction + AI summarization
            return AIHandler.handle(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location, project_status, years)
        elif mode == "summary":
            # RAG+summary mode handles direct retrieval + AI summarization
            return RAGSummaryHandler.handle(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location, project_status, years)
        else:  # mode == "rag"
            # RAG mode handles direct retrieval without summarization
            return RAGHandler.handle(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location, project_status, years)
   
    @classmethod
    def get_document_similarity(cls, document_id, project_ids=None, limit=10):
        """Find documents similar to a given document using document-level embeddings.
        
        Args:
            document_id (str): The document ID to find similar documents for
            project_ids (list, optional): Optional list of project IDs to filter similar documents by
            limit (int): Maximum number of similar documents to return
            
        Returns:
            dict: A dictionary containing:
                - documents (list): Similar documents with similarity scores
                - metrics (dict): Performance metrics
        """
        current_app.logger.info("=== SearchService.get_document_similarity started ===")
        current_app.logger.info(f"Document ID: {document_id}")
        current_app.logger.info(f"Project IDs: {project_ids}")
        current_app.logger.info(f"Limit: {limit}")
        
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        # Call vector search API for document similarity
        current_app.logger.info("Calling VectorSearchClient.document_similarity_search...")
        search_start = time.time()
        result = VectorSearchClient.document_similarity_search(
            document_id, project_ids, limit
        )
        
        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        current_app.logger.info(f"Document similarity search completed in {metrics['search_time_ms']}ms")
        
        # Extract documents from the Vector API response structure
        documents = []
        source_document_id = None
        vector_metrics = {}
        
        if result and "document_similarity" in result:
            similarity_data = result["document_similarity"]
            documents = similarity_data.get("documents", [])
            source_document_id = similarity_data.get("source_document_id", document_id)
            vector_metrics = similarity_data.get("search_metrics", {})
        
        current_app.logger.info(f"Found {len(documents)} similar documents")
        
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        current_app.logger.info(f"SearchService.get_document_similarity completed in {metrics['total_time_ms']}ms")
        current_app.logger.info("=== SearchService.get_document_similarity completed ===")

        return {
            "result": {
                "source_document_id": source_document_id,
                "documents": documents,
                "metrics": {
                    **metrics,
                    "vector_search_metrics": vector_metrics
                }
            }
        }

    @classmethod
    def _determine_auto_mode(cls, query: str, user_location: dict = None, metrics: dict = None) -> str:
        """Determine the optimal processing mode based on query complexity analysis.
        
        Uses the complexity analyzer to determine whether the query needs:
        - rag: Simple content search
        - summary: RAG + summarization
        - ai: Parameter extraction + AI processing
        - agent: Advanced multi-step reasoning
        
        Args:
            query: The user query to analyze
            user_location: Optional user location data
            metrics: Metrics dictionary to track analysis
            
        Returns:
            The optimal mode string ("rag", "summary", "ai", or "agent")
        """
        try:
            current_app.logger.info("🤖 AUTO MODE: Starting complexity analysis...")
            
            # Use the same complexity analyzer as AI/agent modes
            from search_api.services.generation.implementations.openai.openai_query_complexity_analyzer import OpenAIQueryComplexityAnalyzer
            complexity_analyzer = OpenAIQueryComplexityAnalyzer()
            
            # Analyze query complexity
            complexity_result = complexity_analyzer.analyze_query_complexity(query, user_location)
            complexity_tier = complexity_result.get("complexity_tier", "simple")
            complexity_reason = complexity_result.get("reason", "Unknown")
            
            current_app.logger.info(f"🤖 AUTO MODE: Complexity analysis result: {complexity_tier}")
            current_app.logger.info(f"🤖 AUTO MODE: Reason: {complexity_reason}")
            
            # Store complexity analysis in metrics
            if metrics is not None:
                metrics["auto_complexity_analysis"] = complexity_result
            
            # Map complexity tiers to processing modes
            if complexity_tier == "simple":
                # Simple queries get RAG + summarization for better user experience
                selected_mode = "summary"
                current_app.logger.info("🤖 AUTO MODE: Simple query detected → Using 'summary' mode (RAG + AI summarization)")
            elif complexity_tier == "complex":
                # Complex queries need parameter extraction but not agent reasoning
                selected_mode = "ai"
                current_app.logger.info("🤖 AUTO MODE: Complex query detected → Using 'ai' mode (parameter extraction + processing)")
            elif complexity_tier == "agent_required":
                # Agent-required queries need full multi-step reasoning
                selected_mode = "agent"
                current_app.logger.info("🤖 AUTO MODE: Agent-required query detected → Using 'agent' mode (advanced reasoning)")
            else:
                # Fallback to AI mode for unknown complexity
                selected_mode = "ai"
                current_app.logger.warning(f"🤖 AUTO MODE: Unknown complexity tier '{complexity_tier}' → Defaulting to 'ai' mode")
            
            return selected_mode
            
        except Exception as e:
            current_app.logger.error(f"🤖 AUTO MODE: Error during complexity analysis: {e}")
            current_app.logger.error(f"🤖 AUTO MODE: Falling back to 'ai' mode")
            return "ai"  # Safe fallback that handles most queries well