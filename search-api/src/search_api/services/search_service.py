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
                                     will use LLM services to analyze the query and suggest appropriate filters.
            
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
        
        # Initialize metrics and timing
        metrics = {}
        start_time = time.time()
        metrics["start_time"] = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        metrics["agentic_mode"] = agentic
        
        # Handle parameter extraction based on mode
        if agentic:
            parameters = cls._handle_agentic_mode(query, project_ids, document_type_ids, search_strategy, inference, metrics)
        else:
            parameters = cls._handle_rag_mode(query, project_ids, document_type_ids, search_strategy, inference, metrics)
        
        # Check for early exit (non-EAO query in agentic mode)
        if len(parameters) == 5 and isinstance(parameters[4], dict) and parameters[4].get('early_exit'):
            early_exit_info = parameters[4]
            current_app.logger.info(f"Early exit triggered: {early_exit_info.get('reason', 'unknown')}")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            
            return {
                "result": {
                    "response": early_exit_info.get('response', 'Query appears to be outside EAO scope.'),
                    "documents": [],
                    "metrics": metrics,
                    "search_quality": "not_applicable",
                    "project_inference": {},
                    "document_type_inference": {},
                    "early_exit": True,
                    "exit_reason": early_exit_info.get('reason', 'query_out_of_scope')
                }
            }
        
        # Extract search parameters
        project_ids, document_type_ids, search_strategy, semantic_query = parameters[:4]
        
        # Execute vector search
        search_result = cls._execute_vector_search(query, project_ids, document_type_ids, inference, ranking, search_strategy, semantic_query, metrics)
        
        # Check if search returned no results
        if not search_result["documents_or_chunks"]:
            current_app.logger.warning("No documents found - returning empty result")
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
        
        # Generate response summary based on mode
        if agentic:
            summary_result = cls._generate_agentic_summary(search_result["documents_or_chunks"], query, metrics)
        else:
            summary_result = cls._generate_rag_summary(search_result["documents_or_chunks"], query, metrics)
        
        # Handle summary generation errors
        if isinstance(summary_result, dict) and "error" in summary_result:
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
        
        # Finalize metrics and logging
        metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        # Log final summary
        if agentic:
            cls._log_agentic_summary(metrics, search_result["search_duration"], search_result["search_quality"], search_result["documents_or_chunks"], query)
        else:
            cls._log_basic_summary(search_result["documents_or_chunks"], query)
        
        current_app.logger.info("=== SearchService.get_documents_by_query completed ===")
        
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
    def _handle_rag_mode(cls, query, project_ids, document_type_ids, search_strategy, inference, metrics):
        """Handle RAG mode (non-agentic) processing - use provided parameters directly.
        
        Args:
            query (str): The user's search query
            project_ids (list): Project IDs (may be None)
            document_type_ids (list): Document type IDs (may be None) 
            search_strategy (str): Search strategy (may be None)
            inference (list): Inference settings
            metrics (dict): Metrics dictionary to update
            
        Returns:
            tuple: (project_ids, document_type_ids, search_strategy, semantic_query)
        """
        current_app.logger.info("=== RAG MODE: Using provided parameters directly ===")
        
        # Initialize metrics for non-agentic mode
        metrics["agentic_time_ms"] = 0.0
        metrics["agentic_suggestions"] = {}
        metrics["agentic_project_extraction"] = False
        metrics["agentic_document_type_extraction"] = False
        metrics["agentic_semantic_query_generated"] = False
        metrics["agentic_strategy_extraction"] = False
        metrics["agentic_strategy_time_ms"] = 0.0
        metrics["relevance_check_time_ms"] = 0.0
        metrics["query_relevance"] = {"checked": False}
        
        # In RAG mode, we don't modify the query - use original
        semantic_query = None
        
        current_app.logger.info(f"RAG MODE: Final parameters - Project IDs: {project_ids}, Document Types: {document_type_ids}, Search Strategy: {search_strategy}")
        current_app.logger.info("=== RAG MODE: Parameter setup complete ===")
        
        return project_ids, document_type_ids, search_strategy, semantic_query

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
        
        # Log agentic-specific metrics if available
        if metrics.get('agentic_time_ms'):
            current_app.logger.info(f"🤖 Agentic processing time: {metrics['agentic_time_ms']}ms")
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
    def _handle_agentic_mode(cls, query, project_ids, document_type_ids, search_strategy, inference, metrics):
        """Handle agentic mode processing using direct LLM parameter extraction.
        
        Uses direct LLM integration for intelligent parameter extraction and query optimization.
        
        Args:
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
        current_app.logger.info("=== AGENTIC MODE: Starting direct LLM parameter extraction ===")
        
        # Step 1: Validate query relevance to EAO scope
        current_app.logger.info("🔍 VALIDATION: Checking query relevance to EAO scope...")
        try:
            from search_api.services.generation.factories import QueryValidatorFactory
            
            validation_start = time.time()
            query_validator = QueryValidatorFactory.create_validator()
            validation_result = query_validator.validate_query_relevance(query)
            
            validation_time = round((time.time() - validation_start) * 1000, 2)
            metrics["query_validation_time_ms"] = validation_time
            metrics["query_validation_result"] = validation_result
            
            current_app.logger.info(f"🔍 VALIDATION: Query relevance check completed in {validation_time}ms")
            current_app.logger.info(f"🔍 VALIDATION: Relevant={validation_result['is_relevant']}, Confidence={validation_result['confidence']}")
            
            # Check if query is not relevant to EAO scope
            if not validation_result['is_relevant'] and validation_result['recommendation'] == 'inform_user_out_of_scope':
                current_app.logger.info("🔍 VALIDATION: Query is out of scope - triggering early exit")
                
                early_exit_info = {
                    'early_exit': True,
                    'reason': 'query_out_of_scope',
                    'response': validation_result.get('suggested_response', 
                        "I'm designed to help with Environmental Assessment Office (EAO) related queries about environmental assessments, projects, and regulatory processes in British Columbia. Your question appears to be outside this scope. Please ask about environmental assessments, projects under review, or EAO processes."),
                    'validation_result': validation_result
                }
                
                return project_ids, document_type_ids, search_strategy, query, early_exit_info
                
        except Exception as e:
            current_app.logger.warning(f"🔍 VALIDATION: Query validation failed: {e} - proceeding with search")
            metrics["query_validation_error"] = str(e)
        
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
                # Get available document types from vector search API
                document_types_data = VectorSearchClient.get_document_types()
                available_document_types = {}
                
                if isinstance(document_types_data, dict) and document_types_data:
                    available_document_types = document_types_data.get('document_types', {})
                    current_app.logger.info(f"🤖 LLM: Found {len(available_document_types)} available document types")
                
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
            
            if not document_type_ids and extraction_result.get('document_type_ids'):
                document_type_ids = extraction_result['document_type_ids']
                current_app.logger.info(f"🤖 LLM: Extracted document type IDs: {document_type_ids}")
            
            # Apply extracted search strategy if not already provided
            if not search_strategy and extraction_result.get('search_strategy'):
                search_strategy = extraction_result['search_strategy']
                current_app.logger.info(f"🤖 LLM: Extracted search strategy: {search_strategy}")
            
            # Use semantic query if available
            semantic_query = extraction_result.get('semantic_query', query)
            if semantic_query != query:
                current_app.logger.info(f"🤖 LLM: Generated semantic query: '{semantic_query}'")
            
            # Record metrics
            metrics["agentic_time_ms"] = round((time.time() - agentic_start) * 1000, 2)
            metrics["agentic_extraction"] = extraction_result
            metrics["agentic_project_extraction"] = bool(extraction_result.get('project_ids'))
            metrics["agentic_document_type_extraction"] = bool(extraction_result.get('document_type_ids'))
            metrics["agentic_semantic_query_generated"] = semantic_query != query
            metrics["agentic_extraction_confidence"] = extraction_result.get('confidence', 0.0)
            metrics["agentic_extraction_provider"] = ParameterExtractorFactory.get_provider()
            
            # Add extraction summary for clarity
            extraction_sources = extraction_result.get('extraction_sources', {})
            metrics["agentic_extraction_summary"] = {
                "llm_calls_made": sum(1 for source in extraction_sources.values() if source in ["llm_extracted", "llm_optimized"]),
                "parameters_supplied": sum(1 for source in extraction_sources.values() if source == "supplied"),
                "parameters_extracted": sum(1 for source in extraction_sources.values() if source == "llm_extracted"),
                "parameters_fallback": sum(1 for source in extraction_sources.values() if source == "fallback")
            }
            
            current_app.logger.info(f"🤖 LLM: Parameter extraction completed in {metrics['agentic_time_ms']}ms using {ParameterExtractorFactory.get_provider()} (confidence: {extraction_result.get('confidence', 0.0)})")
            
        except Exception as e:
            current_app.logger.error(f"🤖 LLM: Error during parameter extraction: {e}")
            metrics["agentic_error"] = str(e)
            metrics["agentic_time_ms"] = round((time.time() - agentic_start) * 1000, 2) if 'agentic_start' in locals() else 0
            # Continue with original parameters
            semantic_query = query
        
        current_app.logger.info(f"🤖 LLM: Final parameters - Project IDs: {project_ids}, Document Types: {document_type_ids}, Search Strategy: {search_strategy}")
        current_app.logger.info("=== AGENTIC MODE: Direct LLM analysis complete ===")
        
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
