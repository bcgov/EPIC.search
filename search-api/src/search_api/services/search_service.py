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
from search_api.clients.vector_search_client import VectorSearchClient


class SearchService:
    """Service class for handling search operations.
    
    This class coordinates the interaction between vector search and LLM components,
    manages performance metrics collection, and handles the overall search flow.
    """

    @classmethod
    def get_documents_by_query(cls, query, project_ids=None, document_type_ids=None, inference=None, ranking=None, search_strategy=None, agentic=False):
        """Process a user query to retrieve and synthesize relevant information.
        
        This method orchestrates the complete search flow:
        1. Initializes performance metrics
        2. [AGENTIC MODE] Optionally uses LLM to extract project/filter info from natural language
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
            agentic (bool, optional): If True, enables agentic mode where LLM will intelligently 
                                     extract project IDs and filters from natural language queries.
                                     When enabled and no project_ids/inference provided, the system
                                     will use MCP tools to analyze the query and suggest appropriate filters.
            
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
        current_app.logger.info(f"Agentic Mode: {agentic}")
        
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        metrics["agentic_mode"] = agentic
        
        # Handle agentic mode processing
        agentic_result = cls._handle_agentic_mode(
            agentic, query, project_ids, document_type_ids, search_strategy, inference, metrics
        )
        
        # Check if we got an early exit (non-EAO query)
        if len(agentic_result) == 5 and isinstance(agentic_result[4], dict) and agentic_result[4].get('early_exit'):
            early_exit_info = agentic_result[4]
            current_app.logger.info(f"Early exit triggered: {early_exit_info.get('reason', 'unknown')}")
            
            # Total execution time for early exit
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
            # Return early with the suggested response
            return {
                "result": {
                    "response": early_exit_info.get('response', 'Query appears to be outside EAO scope.'),
                    "documents": [],  # No documents for out-of-scope queries
                    "metrics": metrics,
                    "search_quality": "not_applicable",
                    "project_inference": {},
                    "document_type_inference": {},
                    "early_exit": True,
                    "exit_reason": early_exit_info.get('reason', 'query_out_of_scope')
                }
            }
        
        # Normal case - extract the parameters
        project_ids, document_type_ids, search_strategy, semantic_query = agentic_result[:4]

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
        metrics["search_time_ms"] = round((time.time() - search_start) * 1000, 2)
        metrics["search_breakdown"] = search_breakdown if search_breakdown else search_metrics  # Include detailed search breakdown metrics
        metrics["search_quality"] = search_quality # Add quality metrics from vector search API
        metrics["original_query"] = original_query # Original user query before processing
        metrics["final_semantic_query"] = final_semantic_query # Final processed query for semantic search
        metrics["semantic_cleaning_applied"] = semantic_cleaning_applied # Whether query cleaning was applied
        metrics["search_mode"] = search_mode # Search mode used by vector search
        metrics["query_processed"] = query_processed # Whether query underwent processing
        metrics["inference_settings"] = inference_settings # Inference configuration details
        
        # Check if we have documents/chunks and log detailed info
        if not documents_or_chunks:
            current_app.logger.warning("No documents_or_chunks found - returning empty result")
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
        elif isinstance(documents_or_chunks, list) and len(documents_or_chunks) == 0:
            current_app.logger.warning("Documents list is empty - returning empty result")
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
        else:
            current_app.logger.info(f"Found {len(documents_or_chunks)} documents/chunks - proceeding with LLM processing")

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
                "response": response.get("response", "No response generated") if isinstance(response, dict) else str(response),
                documents_key: documents_or_chunks,  # Always use the original documents_or_chunks
                "metrics": metrics,
                "search_quality": search_quality,
                "project_inference": project_inference,
                "document_type_inference": document_type_inference
            }
        }

    @classmethod
    def _handle_agentic_mode(cls, agentic, query, project_ids, document_type_ids, search_strategy, inference, metrics):
        """Handle agentic mode processing for intelligent parameter extraction.
        
        Args:
            agentic (bool): Whether agentic mode is enabled
            query (str): The user's search query
            project_ids (list): Current project IDs (may be None)
            document_type_ids (list): Current document type IDs (may be None)
            search_strategy (str): Current search strategy (may be None)
            inference (list): Inference settings
            metrics (dict): Metrics dictionary to update
            
        Returns:
            tuple: (project_ids, document_type_ids, search_strategy, semantic_query) or
                   (project_ids, document_type_ids, search_strategy, semantic_query, early_exit_info)
                   when early exit is triggered for non-EAO queries
        """
        # Initialize semantic query variable
        semantic_query = None
        
        # AGENTIC MODE: Intelligent parameter extraction from natural language
        if agentic:
            current_app.logger.info("=== AGENTIC MODE: Analyzing query for intelligent parameter extraction ===")
            
            # STEP 1: Check query relevance to EAO upfront
            current_app.logger.info("🤖 AGENTIC: Checking query relevance to EAO...")
            try:
                from search_api.services.agentic_service import AgenticService
                
                relevance_start = time.time()
                relevance_check = AgenticService.check_query_relevance(query, context="Query relevance validation")
                
                if relevance_check and 'result' in relevance_check:
                    relevance_result = relevance_check['result']
                    is_eao_relevant = relevance_result.get('is_eao_relevant', True)
                    relevance_confidence = relevance_result.get('confidence', 0.5)
                    relevance_reasoning = relevance_result.get('reasoning', [])
                    recommendation = relevance_result.get('recommendation', 'proceed_with_search')
                    suggested_response = relevance_result.get('suggested_response', None)
                    
                    # Record relevance check metrics
                    metrics["relevance_check_time_ms"] = round((time.time() - relevance_start) * 1000, 2)
                    metrics["query_relevance"] = {
                        "is_eao_relevant": is_eao_relevant,
                        "confidence": relevance_confidence,
                        "reasoning": relevance_reasoning,
                        "recommendation": recommendation
                    }
                    
                    current_app.logger.info(f"🤖 AGENTIC: Query relevance - Relevant: {is_eao_relevant}, Confidence: {relevance_confidence}")
                    current_app.logger.info(f"🤖 AGENTIC: Reasoning: {', '.join(relevance_reasoning[:2])}")
                    
                    # If query is not EAO-relevant, return early with suggested response
                    if not is_eao_relevant and recommendation == "inform_user_out_of_scope" and suggested_response:
                        current_app.logger.info("🤖 AGENTIC: Query determined to be out of scope - returning early")
                        metrics["agentic_early_exit"] = True
                        metrics["agentic_time_ms"] = round((time.time() - relevance_start) * 1000, 2)
                        
                        # Return tuple indicating early exit with the suggested response
                        return project_ids, document_type_ids, search_strategy, None, {
                            "early_exit": True,
                            "response": suggested_response,
                            "reason": "query_out_of_scope"
                        }
                else:
                    current_app.logger.warning("🤖 AGENTIC: No relevance check result - proceeding with query")
                    metrics["relevance_check_time_ms"] = round((time.time() - relevance_start) * 1000, 2)
                    metrics["query_relevance"] = {"error": "No relevance result received"}
                    
            except Exception as relevance_error:
                current_app.logger.error(f"🤖 AGENTIC: Error during query relevance check: {relevance_error}")
                metrics["relevance_check_time_ms"] = round((time.time() - relevance_start) * 1000, 2) if 'relevance_start' in locals() else 0
                metrics["query_relevance"] = {"error": str(relevance_error)}
                # Continue with normal processing if relevance check fails
            
            # STEP 2: Continue with normal agentic processing for relevant queries
            current_app.logger.info("🤖 AGENTIC: Query passed relevance check - proceeding with parameter extraction")
            
            # Determine what the agent should extract based on inference settings
            should_extract_projects = not project_ids and (not inference or "PROJECT" not in inference)
            should_extract_document_types = not document_type_ids and (not inference or "DOCUMENTTYPE" not in inference)
            should_suggest_search_strategy = not search_strategy  # Suggest strategy if none provided
            
            # Always run semantic query cleaning in agentic mode
            should_clean_query = True
            
            current_app.logger.info(f"🤖 AGENTIC: Should extract projects: {should_extract_projects}")
            current_app.logger.info(f"🤖 AGENTIC: Should extract document types: {should_extract_document_types}")
            current_app.logger.info(f"🤖 AGENTIC: Should suggest search strategy: {should_suggest_search_strategy}")
            current_app.logger.info(f"🤖 AGENTIC: Should clean query: {should_clean_query}")
            
            if should_extract_projects or should_extract_document_types or should_clean_query or should_suggest_search_strategy:
                try:
                    from search_api.services.agentic_service import AgenticService
                    
                    agentic_start = time.time()
                    current_app.logger.info("Using MCP tools to analyze query and suggest filters...")
                    
                    # Use the agentic service to get intelligent filter suggestions
                    filter_suggestions = AgenticService.suggest_filters(query, context="Intelligent project and filter extraction")
                    
                    # Extract MCP-suggested filters
                    if filter_suggestions and 'result' in filter_suggestions:
                        agentic_result = filter_suggestions['result']
                        suggested_filters = agentic_result.get('recommended_filters', {})
                        suggested_project_ids = suggested_filters.get('project_ids', [])
                        suggested_document_type_ids = suggested_filters.get('document_type_ids', [])
                        suggested_semantic_query = suggested_filters.get('semantic_query', None)
                        
                        # Apply intelligent suggestions based on what we should extract
                        if should_extract_projects and suggested_project_ids:
                            project_ids = suggested_project_ids
                            current_app.logger.info(f"🤖 AGENTIC: Extracted project IDs from query: {project_ids}")
                            
                        if should_extract_document_types and suggested_document_type_ids:
                            document_type_ids = suggested_document_type_ids  
                            current_app.logger.info(f"🤖 AGENTIC: Extracted document type IDs from query: {document_type_ids}")
                        
                        # Always use semantic query if provided (clean query with project/doc type noise removed)
                        semantic_query = None
                        if should_clean_query and suggested_semantic_query and suggested_semantic_query.strip():
                            semantic_query = suggested_semantic_query.strip()
                            current_app.logger.info(f"🤖 AGENTIC: Using cleaned semantic query: '{semantic_query}' (original: '{query}')")
                        
                        # AI-powered search strategy suggestion if no strategy provided
                        if should_suggest_search_strategy:
                            current_app.logger.info("🤖 AGENTIC: Getting search strategy suggestion...")
                            strategy_start = time.time()
                            
                            try:
                                # Use the query for strategy analysis (prefer semantic_query if available)
                                analysis_query = semantic_query if semantic_query else query
                                
                                # Get search strategy recommendation from MCP tools
                                strategy_suggestion = AgenticService.suggest_search_strategy(
                                    query=analysis_query,
                                    context="Intelligent search strategy selection",
                                    user_intent="find_documents"  # Could be enhanced with actual user intent
                                )
                                
                                if strategy_suggestion and 'result' in strategy_suggestion:
                                    strategy_result = strategy_suggestion['result']
                                    suggested_strategy = strategy_result.get('recommended_strategy', 'HYBRID_SEMANTIC_FALLBACK')
                                    strategy_confidence = strategy_result.get('confidence', 0.7)
                                    strategy_explanation = strategy_result.get('explanation', 'Strategy recommended by AI analysis')
                                    
                                    search_strategy = suggested_strategy
                                    current_app.logger.info(f"🤖 AGENTIC: Recommended search strategy: {search_strategy} (confidence: {strategy_confidence})")
                                    current_app.logger.info(f"🤖 AGENTIC: Strategy explanation: {strategy_explanation}")
                                    
                                    # Add strategy metrics
                                    metrics["agentic_strategy_suggestion"] = strategy_result
                                    metrics["agentic_strategy_extraction"] = True
                                    metrics["agentic_strategy_time_ms"] = round((time.time() - strategy_start) * 1000, 2)
                                    
                                else:
                                    current_app.logger.warning("🤖 AGENTIC: No strategy suggestion received from MCP tools")
                                    metrics["agentic_strategy_extraction"] = False
                                    metrics["agentic_strategy_error"] = "No strategy suggestions received"
                                    metrics["agentic_strategy_time_ms"] = round((time.time() - strategy_start) * 1000, 2)
                                    
                            except Exception as strategy_error:
                                current_app.logger.error(f"🤖 AGENTIC: Error during search strategy suggestion: {strategy_error}")
                                metrics["agentic_strategy_extraction"] = False
                                metrics["agentic_strategy_error"] = str(strategy_error)
                                metrics["agentic_strategy_time_ms"] = round((time.time() - strategy_start) * 1000, 2)
                                # Continue with no strategy (will use vector API default)
                        else:
                            current_app.logger.info(f"🤖 AGENTIC: Using provided search strategy: {search_strategy}")
                            metrics["agentic_strategy_extraction"] = False
                            metrics["agentic_strategy_time_ms"] = 0.0
                        
                        # Record agentic metrics - store full agentic result, not just filters
                        metrics["agentic_time_ms"] = round((time.time() - agentic_start) * 1000, 2)
                        metrics["agentic_suggestions"] = agentic_result  # Store full result instead of just recommended_filters
                        metrics["agentic_project_extraction"] = should_extract_projects and bool(suggested_project_ids)
                        metrics["agentic_document_type_extraction"] = should_extract_document_types and bool(suggested_document_type_ids)
                        metrics["agentic_semantic_query_generated"] = bool(semantic_query)
                        
                        current_app.logger.info(f"🤖 AGENTIC: Parameter extraction completed in {metrics['agentic_time_ms']}ms")
                    else:
                        current_app.logger.warning("🤖 AGENTIC: No filter suggestions received from MCP tools")
                        metrics["agentic_time_ms"] = round((time.time() - agentic_start) * 1000, 2)
                        metrics["agentic_error"] = "No filter suggestions received"
                        metrics["agentic_strategy_extraction"] = False
                        metrics["agentic_strategy_time_ms"] = 0.0
                        
                except Exception as e:
                    current_app.logger.error(f"🤖 AGENTIC: Error during intelligent parameter extraction: {e}")
                    metrics["agentic_error"] = str(e)
                    metrics["agentic_time_ms"] = round((time.time() - agentic_start) * 1000, 2) if 'agentic_start' in locals() else 0
                    metrics["agentic_strategy_extraction"] = False
                    metrics["agentic_strategy_time_ms"] = 0.0
                    # Continue with original parameters
            else:
                current_app.logger.info("🤖 AGENTIC: No extraction needed - using provided parameters")
                metrics["agentic_time_ms"] = 0.0
                metrics["agentic_suggestions"] = {}
                metrics["agentic_project_extraction"] = False
                metrics["agentic_document_type_extraction"] = False
                metrics["agentic_semantic_query_generated"] = False
                metrics["agentic_strategy_extraction"] = False
                metrics["agentic_strategy_time_ms"] = 0.0
                
            current_app.logger.info(f"🤖 AGENTIC: Final parameters - Project IDs: {project_ids}, Document Types: {document_type_ids}, Search Strategy: {search_strategy}, Inference: {inference}")
            current_app.logger.info("=== AGENTIC MODE: Analysis complete ===")
        else:
            # Non-agentic mode
            current_app.logger.info("=== NON-AGENTIC MODE: Using provided parameters directly ===")
            metrics["agentic_time_ms"] = 0.0
            metrics["agentic_suggestions"] = {}
            metrics["agentic_project_extraction"] = False
            metrics["agentic_document_type_extraction"] = False
            metrics["agentic_semantic_query_generated"] = False
            metrics["agentic_strategy_extraction"] = False
            metrics["agentic_strategy_time_ms"] = 0.0
            metrics["relevance_check_time_ms"] = 0.0
            metrics["query_relevance"] = {"checked": False}
        
        return project_ids, document_type_ids, search_strategy, semantic_query

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
        current_app.logger.info(f"Found {len(result.get('documents', [])) if isinstance(result, dict) and result.get('documents') else 0} similar documents")
        
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        current_app.logger.info(f"SearchService.get_document_similarity completed in {metrics['total_time_ms']}ms")
        current_app.logger.info("=== SearchService.get_document_similarity completed ===")

        return {
            "result": {
                "documents": result.get("documents", []),
                "metrics": metrics
            }
        }
