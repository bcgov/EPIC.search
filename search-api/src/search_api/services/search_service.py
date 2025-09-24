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
from search_api.clients.vector_search_client import VectorSearchClient

class SearchService:
    """Service class for handling search operations.
    
    This class coordinates the interaction between vector search and LLM components,
    manages performance metrics collection, and handles the overall search flow.
    """

    @classmethod
    def get_documents_by_query(cls, query, project_ids=None, document_type_ids=None, inference=None, ranking=None, search_strategy=None, mode="rag", user_location=None):
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
        if mode == "agent":
            # Agent mode handles entire query processing internally
            return cls._handle_agent_mode(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location)
        elif mode == "ai":
            # AI mode handles LLM parameter extraction + AI summarization
            return cls._handle_ai_mode(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location, mode)
        elif mode == "summary":
            # RAG+summary mode handles direct retrieval + AI summarization
            return cls._handle_rag_with_summary_mode(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location)
        else:  # mode == "rag"
            # RAG mode handles direct retrieval without summarization
            return cls._handle_rag_mode(query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location)

    @classmethod
    def _handle_rag_mode(cls, query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location=None):
        """Handle RAG mode processing - direct retrieval without summarization.
        
        RAG mode performs:
        - Query relevance check up front
        - Direct vector search with provided parameters (no AI extraction)
        - Returns raw search results without summarization
        
        Args:
            query: The user query
            project_ids: Optional user-provided project IDs
            document_type_ids: Optional user-provided document type IDs  
            search_strategy: Optional user-provided search strategy
            inference: Inference settings
            ranking: Optional ranking configuration
            metrics: Metrics dictionary to update
            user_location: Optional user location data
            
        Returns:
            Complete response dictionary with RAG results
        """
        start_time = time.time()
        current_app.logger.info("=== RAG MODE: Starting direct retrieval processing ===")
        
        # Initialize metrics for RAG mode
        metrics["ai_processing_time_ms"] = 0.0
        metrics["ai_suggestions"] = {}
        metrics["ai_project_extraction"] = False
        metrics["ai_document_type_extraction"] = False
        metrics["ai_semantic_query_generated"] = False
        metrics["ai_strategy_extraction"] = False
        metrics["ai_strategy_time_ms"] = 0.0
        
        # Execute vector search with provided parameters
        current_app.logger.info("🔍 RAG MODE: Executing vector search...")
        semantic_query = None  # RAG mode doesn't modify the query
        
        search_result = cls._execute_vector_search(
            query, project_ids, document_type_ids, inference, ranking, 
            search_strategy, semantic_query, metrics
        )
        
        # Check if search returned no results
        if not search_result["documents_or_chunks"]:
            current_app.logger.warning("🔍 RAG MODE: No documents found")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": "No relevant information found.",
                    search_result["documents_key"]: [],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Generate basic RAG summary (no AI summarization)
        summary_result = cls._generate_rag_summary(search_result["documents_or_chunks"], query, metrics)
        
        # Handle summary generation errors
        if isinstance(summary_result, dict) and "error" in summary_result:
            current_app.logger.error("🔍 RAG MODE: Summary generation failed")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": summary_result.get("fallback_response", "An error occurred while processing your request."),
                    search_result["documents_key"]: search_result["documents_or_chunks"],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Calculate final metrics
        total_time = round((time.time() - start_time) * 1000, 2)
        metrics["total_time_ms"] = total_time
        
        # Log summary
        cls._log_basic_summary(search_result["documents_or_chunks"], query)
        
        current_app.logger.info("=== RAG MODE: Processing completed ===")
        
        return {
            "result": {
                "response": summary_result.get("response", "No response generated"),
                search_result["documents_key"]: search_result["documents_or_chunks"],
                "metrics": metrics,
                "search_quality": search_result["search_quality"],
                "project_inference": search_result["project_inference"],
                "document_type_inference": search_result["document_type_inference"]
            }
        }

    @classmethod
    def _handle_rag_with_summary_mode(cls, query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location=None):
        """Handle RAG with summary mode processing - retrieval plus AI summarization.
        
        RAG with summary mode performs:
        - Query relevance check up front
        - Direct vector search with provided parameters (no AI extraction)
        - AI summarization of search results
        
        Args:
            query: The user query
            project_ids: Optional user-provided project IDs
            document_type_ids: Optional user-provided document type IDs  
            search_strategy: Optional user-provided search strategy
            inference: Inference settings
            ranking: Optional ranking configuration
            metrics: Metrics dictionary to update
            user_location: Optional user location data
            
        Returns:
            Complete response dictionary with RAG+summary results
        """
        start_time = time.time()
        current_app.logger.info("=== RAG+SUMMARY MODE: Starting retrieval + summarization processing ===")
        
        # Initialize metrics for RAG+summary mode
        metrics["ai_processing_time_ms"] = 0.0
        metrics["ai_suggestions"] = {}
        metrics["ai_project_extraction"] = False
        metrics["ai_document_type_extraction"] = False
        metrics["ai_semantic_query_generated"] = False
        metrics["ai_strategy_extraction"] = False
        metrics["ai_strategy_time_ms"] = 0.0
        
        # Execute vector search with provided parameters
        current_app.logger.info("🔍 RAG+SUMMARY MODE: Executing vector search...")
        semantic_query = None  # RAG+summary mode doesn't modify the query
        
        search_result = cls._execute_vector_search(
            query, project_ids, document_type_ids, inference, ranking, 
            search_strategy, semantic_query, metrics
        )
        
        # Check if search returned no results
        if not search_result["documents_or_chunks"]:
            current_app.logger.warning("🔍 RAG+SUMMARY MODE: No documents found")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": "No relevant information found.",
                    search_result["documents_key"]: [],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Generate AI summary of search results
        current_app.logger.info("🔍 RAG+SUMMARY MODE: Generating AI summary...")
        summary_result = cls._generate_agentic_summary(search_result["documents_or_chunks"], query, metrics)
        
        # Handle summary generation errors
        if isinstance(summary_result, dict) and "error" in summary_result:
            current_app.logger.error("🔍 RAG+SUMMARY MODE: AI summary generation failed")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": summary_result.get("fallback_response", "An error occurred while processing your request."),
                    search_result["documents_key"]: search_result["documents_or_chunks"],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Calculate final metrics
        total_time = round((time.time() - start_time) * 1000, 2)
        metrics["total_time_ms"] = total_time
        
        # Log summary
        cls._log_agentic_summary(metrics, search_result["search_duration"], search_result["search_quality"], search_result["documents_or_chunks"], query)
        
        current_app.logger.info("=== RAG+SUMMARY MODE: Processing completed ===")
        
        return {
            "result": {
                "response": summary_result.get("response", "No response generated"),
                search_result["documents_key"]: search_result["documents_or_chunks"],
                "metrics": metrics,
                "search_quality": search_result["search_quality"],
                "project_inference": search_result["project_inference"],
                "document_type_inference": search_result["document_type_inference"]
            }
        }
       
    @classmethod
    def _execute_vector_search(cls, query, project_ids, document_type_ids, inference, ranking, search_strategy, semantic_query, metrics):
        """Execute vector search and process the response.
        
        Args:
            query (str): The original search query
            project_ids (list): Project IDs for filtering
            document_type_ids (list): Document type IDs for filtering
            inference (list): Inference settings
            ranking (dict): Ranking configuration
            search_strategy (str): Search strategy to use
            semantic_query (str): Processed semantic query (may be None)
            metrics (dict): Metrics dictionary to update

        Returns:
            dict: Search result containing documents_or_chunks, search metadata, etc.
        """
        current_app.logger.info("=== VECTOR SEARCH: Starting search execution ===")

        # Add LLM provider and model information
        metrics["llm_provider"] = os.getenv("LLM_PROVIDER", "ollama")
        if metrics["llm_provider"] == "openai":
            metrics["llm_model"] = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        else:
            metrics["llm_model"] = os.getenv("LLM_MODEL", "")
            
        current_app.logger.info("=== VECTOR SEARCH: Starting search execution ===")
        
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
            query=query, 
            project_ids=project_ids, 
            document_type_ids=document_type_ids, 
            inference=inference, 
            ranking=ranking, 
            search_strategy=search_strategy,
            semantic_query=semantic_query
        )
        search_duration = round((time.time() - search_start) * 1000, 2)
        current_app.logger.info(f"Vector search completed in {search_duration}ms")
        current_app.logger.info(f"Documents/chunks returned: {len(documents_or_chunks) if documents_or_chunks else 0}")
        current_app.logger.info(f"Type of documents_or_chunks: {type(documents_or_chunks)}")
        
        # Extract data from the complete vector API response
        if isinstance(vector_api_response, dict):
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
        else:
            # Fallback if vector_api_response is not a dict (handle string responses)
            current_app.logger.warning(f"Vector API response is not a dict: {type(vector_api_response)}")
            vector_search_data = {}
            search_metrics = {}
            search_quality = "unknown"
            project_inference = {}
            document_type_inference = {}
            original_query = ""
            final_semantic_query = ""
            semantic_cleaning_applied = False
            search_mode = "unknown"
            query_processed = False
            inference_settings = {}
            search_breakdown = {}
        
        # Determine the response type based on what's actually in the vector search data
        if isinstance(vector_api_response, dict) and "vector_search" in vector_api_response:
            vector_search_data = vector_api_response.get("vector_search", {})
            # Check what's actually in the response
            if "documents" in vector_search_data and vector_search_data["documents"]:
                response_type = "documents"
                documents_key = "documents"
            elif "document_chunks" in vector_search_data and vector_search_data["document_chunks"]:
                response_type = "document_chunks"
                documents_key = "document_chunks"
            else:
                # Default to document_chunks if nothing specific found
                response_type = "document_chunks"
                documents_key = "document_chunks"
        else:
            # Default fallback
            response_type = "document_chunks"
            documents_key = "document_chunks"
            
        current_app.logger.info(f"Determined response type: {response_type}, documents_key: {documents_key}")
        
        # Add all search metrics regardless of whether documents were found
        metrics["search_time_ms"] = search_duration
        metrics["search_breakdown"] = search_breakdown if search_breakdown else search_metrics
        metrics["search_quality"] = search_quality
        metrics["original_query"] = original_query
        metrics["final_semantic_query"] = final_semantic_query
        metrics["semantic_cleaning_applied"] = semantic_cleaning_applied
        metrics["search_mode"] = search_mode
        metrics["query_processed"] = query_processed
        metrics["inference_settings"] = inference_settings
        
        current_app.logger.info("=== VECTOR SEARCH: Search execution complete ===")
        
        return {
            "documents_or_chunks": documents_or_chunks,
            "documents_key": documents_key,
            "search_duration": search_duration,
            "search_quality": search_quality,
            "project_inference": project_inference,
            "document_type_inference": document_type_inference
        }
        
    @classmethod
    def _generate_agentic_summary(cls, documents_or_chunks, query, metrics):
        """Generate summary using LLM summarizer from generation package.
        
        Args:
            documents_or_chunks (list): Retrieved documents or document chunks
            query (str): The original search query
            metrics (dict): Metrics dictionary to update
            
        Returns:
            dict: Summary result containing response text or error info
        """
        current_app.logger.info("=== AGENTIC SUMMARY: Starting LLM summarizer from generation package ===")
        
        llm_start = time.time()
        current_app.logger.info(f"Using LLM summarizer for summary: {query}")
        current_app.logger.info(f"Number of documents/chunks for summary: {len(documents_or_chunks) if documents_or_chunks else 0}")
        
        try:
            from search_api.services.generation.factories import SummarizerFactory
            
            summarizer = SummarizerFactory.create_summarizer()
            
            current_app.logger.info("🤖 LLM: Generating summary using LLM summarizer...")
            summary_result = summarizer.summarize_search_results(
                query=query,
                documents_or_chunks=documents_or_chunks,
                search_context={
                    "context": "Agentic search summary",
                    "search_strategy": "agentic",
                    "total_documents": len(documents_or_chunks)
                }
            )
            
            summary_text = summary_result['summary']
            method = summary_result['method']
            confidence = summary_result['confidence']
            provider = summary_result['provider']
            model = summary_result['model']
            
            current_app.logger.info(f"🤖 LLM: Summary generated using method: {method}, provider: {provider}, model: {model}, confidence: {confidence}")
            
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            metrics["agentic_summary_method"] = method
            metrics["agentic_summary_confidence"] = confidence
            metrics["agentic_summary_provider"] = provider
            metrics["agentic_summary_model"] = model
            
            current_app.logger.info("=== AGENTIC SUMMARY: LLM summarizer generation complete ===")
            return {"response": summary_text}
                
        except Exception as e:
            # Log the error and return error info
            current_app.logger.error(f"🤖 LLM: Summary generation error: {str(e)}")
            current_app.logger.error(f"🤖 LLM: Summary error type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"🤖 LLM: Summary error traceback: {traceback.format_exc()}")
            
            metrics["agentic_summary_error"] = str(e)
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            
            current_app.logger.info("=== AGENTIC SUMMARY: Error occurred, returning fallback ===")
            return {
                "error": str(e),
                "fallback_response": "An error occurred while generating the summary. Please try again later."
            }

    @classmethod
    def _generate_rag_summary(cls, documents_or_chunks, query, metrics):
        """Generate basic summary for RAG mode (non-agentic).
        
        Args:
            documents_or_chunks (list): Retrieved documents or document chunks
            query (str): The original search query
            metrics (dict): Metrics dictionary to update
            
        Returns:
            dict: Summary result containing response text
        """
        current_app.logger.info("=== RAG SUMMARY: Generating basic summary ===")
        
        llm_start = time.time()
        current_app.logger.info(f"Using basic response generation for query: {query}")
        current_app.logger.info(f"Number of documents/chunks for basic processing: {len(documents_or_chunks) if documents_or_chunks else 0}")
        
        try:
            # Use the basic response processing method
            response = cls._process_basic_response(documents_or_chunks, query)
            
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            
            current_app.logger.info("=== RAG SUMMARY: Basic summary generation complete ===")
            return {"response": response}
            
        except Exception as e:
            current_app.logger.error(f"Basic summary error: {str(e)}")
            metrics["llm_time_ms"] = round((time.time() - llm_start) * 1000, 2)
            
            return {
                "error": str(e),
                "fallback_response": "An error occurred while processing the documents."
            }

    @classmethod
    def _process_basic_response(cls, documents_or_chunks, query):
        """Process documents for basic mode - just return a simple summary.
        
        Args:
            documents_or_chunks (list): Retrieved documents or document chunks
            query (str): The original search query
            
        Returns:
            str: Basic response string with document count summary
        """
        doc_count = len(documents_or_chunks) if documents_or_chunks else 0
                
        current_app.logger.info(f"Basic mode: returning {doc_count} documents / sections without LLM processing")
        
        return f"Found {doc_count} documents / sections matching your query: '{query[:100]}{'...' if len(query) > 100 else ''}'"

    @classmethod
    def _consolidate_agent_results(cls, main_search_results, agent_results, documents_key):
        """Consolidate and deduplicate agent search results with main search results.
        
        Extracts search results from agent tool executions, deduplicates by document_id,
        and merges with main search results sorted by relevance score.
        
        Args:
            main_search_results (list): Documents from the main vector search
            agent_results (dict): Agent processing results containing tool executions
            documents_key (str): Key name for documents ("documents" or "document_chunks")
            
        Returns:
            tuple: (consolidated_documents, consolidation_metrics)
        """
        if not agent_results or not agent_results.get("agent_attempted"):
            return main_search_results, {"agent_results_found": False}
            
        current_app.logger.info("🔗 CONSOLIDATION: Starting agent result consolidation...")
        current_app.logger.info(f"🔗 CONSOLIDATION: Main search has {len(main_search_results) if main_search_results else 0} {documents_key}")
        current_app.logger.info(f"🔗 CONSOLIDATION: Agent results structure: {type(agent_results)}")
        
        # Extract search results from agent tool executions
        agent_documents = []
        search_executions = 0
        
        tool_executions = agent_results.get("tool_executions", [])
        current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(tool_executions)} total tool executions")
        
        for execution in tool_executions:
            if execution.get("tool") == "search" and execution.get("result", {}).get("success"):
                search_executions += 1
                search_result = execution["result"]["result"]
                
                current_app.logger.info(f"🔗 CONSOLIDATION: === Agent search {search_executions} DETAILED ANALYSIS ===")
                current_app.logger.info(f"🔗 CONSOLIDATION: search_result type: {type(search_result)}")
                current_app.logger.info(f"🔗 CONSOLIDATION: search_result length: {len(search_result) if isinstance(search_result, (list, tuple)) else 'N/A'}")
                
                # Handle different search_result types safely
                original_search_result = search_result
                
                if isinstance(search_result, tuple):
                    current_app.logger.info(f"🔗 CONSOLIDATION: Converting tuple to list for processing")
                    search_result = list(search_result)
                
                if isinstance(search_result, dict):
                    current_app.logger.info(f"🔗 CONSOLIDATION: Dictionary result with keys: {list(search_result.keys())}")
                elif isinstance(search_result, list):
                    current_app.logger.info(f"🔗 CONSOLIDATION: List result with {len(search_result)} elements")
                    if search_result:
                        current_app.logger.info(f"🔗 CONSOLIDATION: First element type: {type(search_result[0])}")
                        if len(search_result) > 1:
                            current_app.logger.info(f"🔗 CONSOLIDATION: Second element type: {type(search_result[1])}")
                else:
                    current_app.logger.warning(f"🔗 CONSOLIDATION: Unexpected result type: {type(search_result)}")
                    continue
                
                # Extract documents/chunks from the search result - try multiple possible keys
                documents_found = []
                
                # Handle the specific agent search result structure: result is an array with two elements
                if isinstance(search_result, list) and len(search_result) >= 2:
                    current_app.logger.info(f"🔗 CONSOLIDATION: Processing agent result array with {len(search_result)} elements")
                    
                    # The data is duplicated in both elements, so we only need to process one
                    # Priority: Use vector_search structure if available (more complete), otherwise use direct array
                    
                    used_vector_search = False
                    
                    # Try second element with vector_search structure first (more complete metadata)
                    if isinstance(search_result[1], dict) and "vector_search" in search_result[1]:
                        vector_search = search_result[1]["vector_search"]
                        if documents_key in vector_search and vector_search[documents_key]:
                            documents_found.extend(vector_search[documents_key])
                            current_app.logger.info(f"🔗 CONSOLIDATION: Used vector_search.{documents_key} with {len(vector_search[documents_key])} documents (avoiding duplication)")
                            used_vector_search = True
                        elif "document_chunks" in vector_search:
                            documents_found.extend(vector_search["document_chunks"])
                            current_app.logger.info(f"🔗 CONSOLIDATION: Used vector_search.document_chunks with {len(vector_search['document_chunks'])} documents (avoiding duplication)")
                            used_vector_search = True
                        elif "documents" in vector_search:
                            documents_found.extend(vector_search["documents"])
                            current_app.logger.info(f"🔗 CONSOLIDATION: Used vector_search.documents with {len(vector_search['documents'])} documents (avoiding duplication)")
                            used_vector_search = True
                    
                    # Fallback: Use first element (direct array) only if we didn't use vector_search
                    if not used_vector_search and isinstance(search_result[0], list):
                        documents_found.extend(search_result[0])
                        current_app.logger.info(f"🔗 CONSOLIDATION: Used direct array with {len(search_result[0])} documents (fallback)")
                    elif not used_vector_search:
                        current_app.logger.warning(f"🔗 CONSOLIDATION: Could not extract documents from agent result structure")
                    else:
                        current_app.logger.info(f"🔗 CONSOLIDATION: Skipped direct array to avoid duplication (used vector_search instead)")
                
                # Fallback: try standard dictionary structure
                elif isinstance(search_result, dict):
                    # Try the expected documents_key first
                    if documents_key in search_result and search_result[documents_key]:
                        documents_found = search_result[documents_key]
                        current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} items using key '{documents_key}'")
                    
                    # Fallback: try both document types
                    elif "document_chunks" in search_result and search_result["document_chunks"]:
                        documents_found = search_result["document_chunks"]
                        current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} document_chunks as fallback")
                    
                    elif "documents" in search_result and search_result["documents"]:
                        documents_found = search_result["documents"]
                        current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} documents as fallback")
                    
                    # Also check if there's a nested result structure
                    elif "result" in search_result:
                        nested_result = search_result["result"]
                        if documents_key in nested_result and nested_result[documents_key]:
                            documents_found = nested_result[documents_key]
                            current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} items in nested result using key '{documents_key}'")
                        elif "document_chunks" in nested_result and nested_result["document_chunks"]:
                            documents_found = nested_result["document_chunks"]
                            current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} document_chunks in nested result")
                        elif "documents" in nested_result and nested_result["documents"]:
                            documents_found = nested_result["documents"]
                            current_app.logger.info(f"🔗 CONSOLIDATION: Found {len(documents_found)} documents in nested result")
                
                if documents_found:
                    agent_documents.extend(documents_found)
                    current_app.logger.info(f"🔗 CONSOLIDATION: Added {len(documents_found)} items from agent search {search_executions}")
                    current_app.logger.info(f"🔗 CONSOLIDATION: Sample agent document keys: {list(documents_found[0].keys()) if documents_found else 'None'}")
                else:
                    current_app.logger.warning(f"🔗 CONSOLIDATION: No documents found in agent search {search_executions}")
                    current_app.logger.warning(f"🔗 CONSOLIDATION: Available search_result keys: {list(search_result.keys()) if isinstance(search_result, dict) and search_result else f'Type: {type(search_result)}'}")
                    if isinstance(search_result, dict):
                        for key, value in search_result.items():
                            current_app.logger.warning(f"🔗 CONSOLIDATION: search_result['{key}'] = {type(value)} with {len(value) if isinstance(value, (list, dict)) else 'N/A'} items")
        
        current_app.logger.info(f"🔗 CONSOLIDATION: Extracted {len(agent_documents)} total items from {search_executions} agent searches")
        
        # Deduplicate by creating a unique identifier for each document/chunk
        all_documents = list(main_search_results) if main_search_results else []
        document_map = {}
        
        def create_unique_id(doc):
            """Create a unique identifier for document or document chunk."""
            doc_id = doc.get("document_id", "")
            page_num = doc.get("page_number", "")
            content = doc.get("content", "")
            
            # For document chunks, use document_id + page_number + content hash for uniqueness
            # For documents, use just document_id
            if page_num or content:
                # This is likely a document chunk - use more specific identifier
                content_hash = str(hash(content[:100])) if content else ""
                return f"{doc_id}_{page_num}_{content_hash}"
            else:
                # This is likely a document - use document_id
                return doc_id
        
        # First, add main search results
        for doc in all_documents:
            unique_id = create_unique_id(doc)
            if unique_id:
                document_map[unique_id] = doc
                
        # Then merge agent results, keeping higher relevance scores
        agent_added = 0
        agent_updated = 0
        
        for doc in agent_documents:
            unique_id = create_unique_id(doc)
            if not unique_id:
                continue
                
            existing_doc = document_map.get(unique_id)
            
            if existing_doc:
                # Update if agent document has higher relevance score
                existing_score = existing_doc.get("relevance_score", 0)
                agent_score = doc.get("relevance_score", 0)
                
                if agent_score > existing_score:
                    document_map[unique_id] = doc
                    agent_updated += 1
            else:
                # Add new document from agent
                document_map[unique_id] = doc
                agent_added += 1
        
        # Convert back to list and sort by relevance score (descending)
        consolidated_documents = list(document_map.values())
        consolidated_documents.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        consolidation_metrics = {
            "agent_results_found": True,
            "agent_search_executions": search_executions,
            "agent_search_documents": len(agent_documents),  # Documents from agent tool searches
            "main_search_documents": len(main_search_results) if main_search_results else 0,  # Documents from primary search
            "agent_documents_added": agent_added,  # New documents added from agent
            "agent_documents_updated": agent_updated,  # Existing documents updated with agent results
            "total_unique_documents": len(consolidated_documents),
            "consolidation_performed": True,
            "documents_key_used": documents_key
        }
        
        current_app.logger.info(f"🔗 CONSOLIDATION: Complete - {consolidation_metrics['main_search_documents']} main + {consolidation_metrics['agent_search_documents']} agent → {consolidation_metrics['total_unique_documents']} unique {documents_key}")
        current_app.logger.info(f"🔗 CONSOLIDATION: Added {agent_added} new, updated {agent_updated} existing {documents_key} from agent results")
        
        return consolidated_documents, consolidation_metrics

    @classmethod
    def _log_agentic_summary(cls, metrics, search_duration, search_quality, documents_or_chunks, query):
        """Log detailed summary for agentic mode with comprehensive metrics and analysis.
        
        Args:
            metrics (dict): Performance and processing metrics
            search_duration (float): Vector search duration in milliseconds
            search_quality (str): Assessed quality of the search results
            documents_or_chunks (list): Retrieved documents or document chunks
            query (str): The original search query
        """
        current_app.logger.info(f"🤖 AGENTIC SUMMARY: Query processing completed successfully")
        current_app.logger.info(f"🤖 Total execution time: {metrics['total_time_ms']}ms")
        current_app.logger.info(f"🤖 Vector search time: {search_duration}ms, LLM time: {metrics.get('llm_time_ms', 'N/A')}ms")
        current_app.logger.info(f"🤖 Search quality assessment: {search_quality}")
        current_app.logger.info(f"🤖 Documents retrieved: {len(documents_or_chunks) if documents_or_chunks else 0}")
        current_app.logger.info(f"🤖 Query processed: '{query[:100]}{'...' if len(query) > 100 else ''}'")
        
        # Log AI processing metrics if available
        if metrics.get('ai_processing_time_ms'):
            current_app.logger.info(f"🤖 AI processing time: {metrics['ai_processing_time_ms']}ms")
        if metrics.get('query_relevance'):
            relevance = metrics['query_relevance']
            current_app.logger.info(f"🤖 Query relevance: {relevance.get('is_eao_relevant', 'N/A')}, "
                                  f"Confidence: {relevance.get('confidence', 'N/A')}")

    @classmethod
    def _log_basic_summary(cls, documents_or_chunks, query):
        """Log basic summary with document count for non-agentic mode.
        
        Args:
            documents_or_chunks (list): Retrieved documents or document chunks
            query (str): The original search query
        """
        doc_count = len(documents_or_chunks) if documents_or_chunks else 0
        doc_type = "documents" if documents_or_chunks and hasattr(documents_or_chunks[0], 'document_id') else "document sections"
        
        current_app.logger.info(f"Search completed: {doc_count} {doc_type} returned for query")
        current_app.logger.info(f"Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")

    @classmethod
    def _handle_ai_mode(cls, query, project_ids, document_type_ids, search_strategy, inference, ranking, metrics, user_location=None, mode="ai"):
        """Handle AI mode processing - LLM parameter extraction plus AI summarization.
        
        AI mode performs:
        - Query relevance check up front
        - LLM-based parameter extraction (projects, document types, strategy)
        - Vector search with optimized parameters
        - AI summarization of search results
        
        Args:
            query: The user query
            project_ids: Optional user-provided project IDs
            document_type_ids: Optional user-provided document type IDs  
            search_strategy: Optional user-provided search strategy
            inference: Inference settings
            ranking: Optional ranking configuration
            metrics: Metrics dictionary to update
            user_location: Optional user location data
            mode: Processing mode ("ai")
            
        Returns:
            Complete response dictionary with AI results
        """
        start_time = time.time()
        current_app.logger.info(f"=== {mode.upper()} MODE: Starting LLM parameter extraction + AI summarization processing ===")
        
        # Check query relevance up front
        current_app.logger.info(f"🔍 {mode.upper()} MODE: Checking query relevance...")
        relevance_start = time.time()
        
        try:
            from search_api.services.generation.factories import QueryValidatorFactory
            relevance_checker = QueryValidatorFactory.create_validator()
            relevance_result = relevance_checker.validate_query_relevance(query)
            
            relevance_time = round((time.time() - relevance_start) * 1000, 2)
            metrics["relevance_check_time_ms"] = relevance_time
            metrics["query_relevance"] = relevance_result
            
            current_app.logger.info(f"🔍 {mode.upper()} MODE: Relevance check completed in {relevance_time}ms: {relevance_result}")
            
            # Handle non-EAO queries
            if not relevance_result.get("is_relevant", True):
                current_app.logger.info(f"🔍 {mode.upper()} MODE: Query not relevant to EAO - returning early")
                metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
                
                return {
                    "result": {
                        "response": relevance_result.get("response", "This query appears to be outside the scope of EAO's mandate."),
                        "documents": [],
                        "metrics": metrics,
                        "search_quality": "not_applicable",
                        "project_inference": {},
                        "document_type_inference": {},
                        "early_exit": True,
                        "exit_reason": "query_not_relevant"
                    }
                }
                
        except Exception as e:
            current_app.logger.error(f"🔍 {mode.upper()} MODE: Relevance check failed: {e}")
            metrics["relevance_check_time_ms"] = round((time.time() - relevance_start) * 1000, 2)
            metrics["query_relevance"] = {"checked": False, "error": str(e)}
        
        # Continue with existing logic but refactored...
        
        # Step 2: Continue with LLM parameter extraction (mode already determined)
        current_app.logger.info(f"� {mode.upper()}: Starting parameter extraction...")
        try:
            from search_api.services.generation.factories import ParameterExtractorFactory
            
            agentic_start = time.time()
            current_app.logger.info("🤖 LLM: Starting parameter extraction from generation package...")
            
            # Fetch available options to provide context to the LLM
            current_app.logger.info("🤖 LLM: Fetching available options for context...")
            
            try:
                # Get available projects from vector search API
                available_projects_list = VectorSearchClient.get_projects_list()
                available_projects = {}
                for project in available_projects_list:
                    if isinstance(project, dict) and 'project_name' in project and 'project_id' in project:
                        available_projects[project['project_name']] = project['project_id']
                
                current_app.logger.info(f"🤖 LLM: Found {len(available_projects)} available projects")
                
            except Exception as e:
                current_app.logger.warning(f"🤖 LLM: Could not fetch projects: {e}")
                available_projects = {}
            
            try:
                # Get available document types from vector search API (now returns normalized array)
                document_types_array = VectorSearchClient.get_document_types()
                available_document_types = {}
                
                # Convert normalized array back to dictionary format expected by parameter extractor
                if isinstance(document_types_array, list):
                    for doc_type in document_types_array:
                        if isinstance(doc_type, dict) and 'document_type_id' in doc_type:
                            doc_type_id = doc_type['document_type_id']
                            available_document_types[doc_type_id] = {
                                'name': doc_type.get('document_type_name', ''),
                                'aliases': doc_type.get('aliases', []),
                                'act': doc_type.get('act', '')
                            }
                    
                    current_app.logger.info(f"🤖 LLM: Converted {len(available_document_types)} document types from normalized array to dictionary format")
                
            except Exception as e:
                current_app.logger.warning(f"🤖 LLM: Could not fetch document types: {e}")
                available_document_types = {}
            
            try:
                # Get available search strategies from vector search API
                strategies_data = VectorSearchClient.get_search_strategies()
                available_strategies = {}
                
                if isinstance(strategies_data, dict):
                    search_strategies = strategies_data.get('search_strategies', {})
                    for strategy_key, strategy_data in search_strategies.items():
                        if isinstance(strategy_data, dict) and 'name' in strategy_data:
                            strategy_name = strategy_data['name']
                            description = strategy_data.get('description', f"Search strategy: {strategy_name}")
                            available_strategies[strategy_name] = description
                    
                    current_app.logger.info(f"🤖 LLM: Found {len(available_strategies)} search strategies")
                
            except Exception as e:
                current_app.logger.warning(f"🤖 LLM: Could not fetch search strategies: {e}")
                available_strategies = {}
            
            # Use LLM parameter extractor from generation package
            parameter_extractor = ParameterExtractorFactory.create_extractor()
            
            extraction_result = parameter_extractor.extract_parameters(
                query=query,
                available_projects=available_projects,
                available_document_types=available_document_types,
                available_strategies=available_strategies,
                supplied_project_ids=project_ids if project_ids else None,
                supplied_document_type_ids=document_type_ids if document_type_ids else None,
                supplied_search_strategy=search_strategy if search_strategy else None
            )
            
            
            # Apply extracted parameters if not already provided
            if not project_ids and extraction_result.get('project_ids'):
                project_ids = extraction_result['project_ids']
                current_app.logger.info(f"🤖 LLM: Extracted project IDs: {project_ids}")
                # Validate project IDs are valid
                if not isinstance(project_ids, list) or not all(isinstance(pid, str) for pid in project_ids):
                    current_app.logger.warning(f"🤖 LLM: Invalid project IDs format, clearing: {project_ids}")
                    project_ids = None
            
            if not document_type_ids and extraction_result.get('document_type_ids'):
                document_type_ids = extraction_result['document_type_ids']
                current_app.logger.info(f"🤖 LLM: Extracted document type IDs: {document_type_ids}")
                # Validate document type IDs are valid  
                if not isinstance(document_type_ids, list) or not all(isinstance(dtid, str) for dtid in document_type_ids):
                    current_app.logger.warning(f"🤖 LLM: Invalid document type IDs format, clearing: {document_type_ids}")
                    document_type_ids = None
            
            # Apply extracted search strategy if not already provided
            if not search_strategy and extraction_result.get('search_strategy'):
                search_strategy = extraction_result['search_strategy']
                current_app.logger.info(f"🤖 LLM: Extracted search strategy: {search_strategy}")
                # Validate search strategy is valid string
                if not isinstance(search_strategy, str) or not search_strategy.strip():
                    current_app.logger.warning(f"🤖 LLM: Invalid search strategy format, clearing: {search_strategy}")
                    search_strategy = None
            
            # Use semantic query if available
            semantic_query = extraction_result.get('semantic_query', query)
            if semantic_query != query:
                current_app.logger.info(f"🤖 LLM: Generated semantic query: '{semantic_query}'")
            
            # Record metrics - use extraction_sources to determine what was actually extracted by AI
            metrics["ai_processing_time_ms"] = round((time.time() - agentic_start) * 1000, 2)
            metrics["ai_extraction"] = extraction_result
            
            # Check if AI actually extracted these parameters (vs supplied or fallback)
            extraction_sources = extraction_result.get('extraction_sources', {})
            metrics["ai_project_extraction"] = extraction_sources.get('project_ids') == 'llm_extracted'
            metrics["ai_document_type_extraction"] = extraction_sources.get('document_type_ids') == 'llm_extracted'
            metrics["ai_semantic_query_generated"] = semantic_query != query
            metrics["ai_extraction_confidence"] = extraction_result.get('confidence', 0.0)
            metrics["ai_extraction_provider"] = ParameterExtractorFactory.get_provider()
            
            # Add extraction summary for clarity
            extraction_sources = extraction_result.get('extraction_sources', {})
            metrics["agentic_extraction_summary"] = {
                "llm_calls_made": sum(1 for source in extraction_sources.values() if source in ["llm_extracted", "llm_optimized"]),
                "parameters_supplied": sum(1 for source in extraction_sources.values() if source == "supplied"),
                "parameters_extracted": sum(1 for source in extraction_sources.values() if source == "llm_extracted"),
                "parameters_fallback": sum(1 for source in extraction_sources.values() if source == "fallback")
            }
            
            current_app.logger.info(f"🤖 LLM: Parameter extraction completed in {metrics['ai_processing_time_ms']}ms using {ParameterExtractorFactory.get_provider()} (confidence: {extraction_result.get('confidence', 0.0)})")
            
        except Exception as e:
            current_app.logger.error(f"🤖 LLM: Error during parameter extraction: {e}")
            metrics["ai_error"] = str(e)
            metrics["ai_processing_time_ms"] = round((time.time() - agentic_start) * 1000, 2) if 'agentic_start' in locals() else 0
        
        # Execute vector search with optimized parameters
        current_app.logger.info(f"🔍 {mode.upper()} MODE: Executing vector search...")
        search_result = cls._execute_vector_search(
            query, project_ids, document_type_ids, inference, ranking, 
            search_strategy, semantic_query, metrics
        )
        
        # Check if search returned no results
        if not search_result["documents_or_chunks"]:
            current_app.logger.warning(f"🔍 {mode.upper()} MODE: No documents found")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": "No relevant information found.",
                    search_result["documents_key"]: [],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Generate AI summary of search results
        current_app.logger.info(f"🔍 {mode.upper()} MODE: Generating AI summary...")
        summary_result = cls._generate_agentic_summary(search_result["documents_or_chunks"], query, metrics)
        
        # Handle summary generation errors
        if isinstance(summary_result, dict) and "error" in summary_result:
            current_app.logger.error(f"🔍 {mode.upper()} MODE: AI summary generation failed")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": summary_result.get("fallback_response", "An error occurred while processing your request."),
                    search_result["documents_key"]: search_result["documents_or_chunks"],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Calculate final metrics
        total_time = round((time.time() - start_time) * 1000, 2)
        metrics["total_time_ms"] = total_time
        
        # Log summary
        cls._log_agentic_summary(metrics, search_result["search_duration"], search_result["search_quality"], search_result["documents_or_chunks"], query)
        
        current_app.logger.info(f"=== {mode.upper()} MODE: Processing completed ===")
        
        return {
            "result": {
                "response": summary_result.get("response", "No response generated"),
                search_result["documents_key"]: search_result["documents_or_chunks"],
                "metrics": metrics,
                "search_quality": search_result["search_quality"],
                "project_inference": search_result["project_inference"],
                "document_type_inference": search_result["document_type_inference"]
            }
        }

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

    @classmethod
    def _handle_agent_mode(cls, query: str, project_ids=None, document_type_ids=None, search_strategy=None, 
                          inference=None, ranking=None, metrics=None, user_location=None) -> dict:
        """Handle agent mode processing - complete query processing via agent stub.
        
        Agent mode delegates the entire query processing to the agent stub, which handles:
        - Multi-step reasoning and planning
        - Multiple RAG calls with different strategies  
        - Result consolidation and deduplication
        - Tool suggestions for API improvements
        
        Args:
            query: The user query
            project_ids: Optional user-provided project IDs
            document_type_ids: Optional user-provided document type IDs  
            search_strategy: Optional user-provided search strategy
            inference: Inference settings
            ranking: Optional ranking configuration
            metrics: Metrics dictionary to update
            user_location: Optional user location data
            
        Returns:
            Complete response dictionary with agent results and summary
        """
        start_time = time.time()
        current_app.logger.info("🤖 AGENT MODE: Starting complete agent processing...")
        
        try:
            # Call agent stub with all user-provided parameters
            from search_api.services.generation.implementations.agent_stub import handle_agent_query
            from search_api.services.generation.factories import LLMClientFactory
            
            # Create LLM client for agent planning
            llm_client = LLMClientFactory.create_client()
            
            agent_result = handle_agent_query(
                query=query,
                reason="Agent mode requested",
                llm_client=llm_client,
                user_location=user_location,
                project_ids=project_ids,
                document_type_ids=document_type_ids,
                search_strategy=search_strategy,
                ranking=ranking
            )
            
            current_app.logger.info("🤖 AGENT MODE: Agent processing completed successfully")
            
            # Update metrics with streamlined agent results
            metrics["agent_processing_time_ms"] = round((time.time() - start_time) * 1000, 2)
            metrics["agent_stub_called"] = True
            
            # Add streamlined agent execution info
            if agent_result:
                # Execution plan (keep as is)
                metrics["execution_plan"] = agent_result.get("execution_plan", [])
                
                # Execution summary with counts
                execution_summary = agent_result.get("execution_summary", {})
                tool_executions = agent_result.get("tool_executions", [])
                
                # Count search executions for consolidation info
                search_count = len([exec for exec in tool_executions if exec.get("tool") == "search"])
                successful_searches = len([exec for exec in tool_executions if exec.get("tool") == "search" and exec.get("result", {}).get("success")])
                
                metrics["agent_execution"] = {
                    "total_steps": execution_summary.get("total_steps", 0),
                    "successful_steps": execution_summary.get("successful_steps", 0), 
                    "failed_steps": execution_summary.get("failed_steps", 0),
                    "search_executions": search_count,
                    "successful_searches": successful_searches
                }
                
                # Consolidation info (only if multiple searches)
                if search_count > 1:
                    consolidated_results = agent_result.get("consolidated_results", {})
                    metrics["agent_consolidation"] = {
                        "multiple_searches_performed": True,
                        "total_documents_consolidated": consolidated_results.get("total_documents", 0),
                        "total_chunks_consolidated": consolidated_results.get("total_chunks", 0)
                    }
                
                # Execution summary - what was actually executed
                tool_executions = agent_result.get("tool_executions", [])
                executed_steps = []
                for execution in tool_executions:
                    step_summary = {
                        "step": execution.get("step"),
                        "tool": execution.get("tool"),
                        "parameters": execution.get("parameters", {}),
                        "success": execution.get("result", {}).get("success", False)
                    }
                    # Add skipped flag if present
                    if execution.get("result", {}).get("skipped"):
                        step_summary["skipped"] = True
                    executed_steps.append(step_summary)
                
                if executed_steps:
                    metrics["steps_executed"] = executed_steps
                
                # Tool suggestions (LLM generates up to 3)
                tool_suggestions = agent_result.get("tool_suggestions", [])
                if tool_suggestions:
                    metrics["tool_suggestions"] = tool_suggestions
            
            # Extract consolidated results from agent
            agent_documents = []
            agent_document_chunks = []
            
            # The agent stub returns consolidated results in its response
            if agent_result and "consolidated_results" in agent_result:
                consolidated = agent_result["consolidated_results"]
                agent_documents = consolidated.get("documents", [])
                agent_document_chunks = consolidated.get("document_chunks", [])
                
                current_app.logger.info(f"🤖 AGENT MODE: Agent returned {len(agent_documents)} documents and {len(agent_document_chunks)} chunks")
            
            # Generate AI summary of the consolidated results
            current_app.logger.info("🤖 AGENT MODE: Generating AI summary of agent results...")
            
            try:
                from search_api.services.generation.factories import SummarizerFactory
                
                summarizer = SummarizerFactory.create_summarizer()
                
                # Combine documents and chunks for summarization
                all_results = agent_documents + agent_document_chunks
                
                if all_results:
                    summary_result = summarizer.summarize_search_results(query, all_results)
                    final_response = summary_result.get("summary", "No summary available")
                    current_app.logger.info("🤖 AGENT MODE: AI summary generated successfully")
                else:
                    final_response = "The agent processing completed but no relevant documents were found."
                    current_app.logger.info("🤖 AGENT MODE: No results to summarize")
                    
                metrics["summary_generated"] = True
                
            except Exception as e:
                current_app.logger.error(f"🤖 AGENT MODE: Summary generation failed: {e}")
                final_response = "The agent found relevant information but summary generation failed."
                metrics["summary_error"] = str(e)
            
            # Calculate final metrics
            total_time = round((time.time() - start_time) * 1000, 2)
            metrics["total_time_ms"] = total_time
            
            # Return complete response (without full agent_result to avoid duplication)
            return {
                "result": {
                    "response": final_response,
                    "documents": agent_documents,
                    "document_chunks": agent_document_chunks,
                    "metrics": metrics,
                    "search_quality": "agent_processed",
                    "project_inference": {},
                    "document_type_inference": {},
                    "agent_processing": True
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"🤖 AGENT MODE: Agent processing failed: {e}")
            
            # Fallback to AI mode on agent failure
            current_app.logger.info("🤖 AGENT MODE: Falling back to AI mode processing...")
            metrics["agent_fallback"] = True
            metrics["agent_error"] = str(e)
            
            return cls._handle_ai_mode(query, project_ids, document_type_ids, search_strategy, 
                                    inference, ranking, metrics, user_location, "ai")
