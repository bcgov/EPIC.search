"""
AI Handler

Handles AI mode processing - LLM parameter extraction plus AI summarization.
"""
import time
from typing import Dict, List, Optional, Any
from flask import current_app

from .base_handler import BaseSearchHandler


class AIHandler(BaseSearchHandler):
    """Handler for AI mode processing - LLM parameter extraction plus AI summarization."""
    
    @classmethod
    def handle(cls, query: str, project_ids: Optional[List[str]] = None, 
               document_type_ids: Optional[List[str]] = None, 
               search_strategy: Optional[str] = None, 
               inference: Optional[List] = None, 
               ranking: Optional[Dict] = None, 
               metrics: Optional[Dict] = None,
               user_location: Optional[Dict] = None,
               location: Optional[Dict] = None, 
               project_status: Optional[str] = None, 
               years: Optional[List] = None) -> Dict[str, Any]:
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
            location: Optional location parameter (user-provided takes precedence)
            project_status: Optional project status parameter (user-provided takes precedence)
            years: Optional years parameter (user-provided takes precedence)
            
        Returns:
            Complete response dictionary with AI results
        """
        start_time = time.time()
        current_app.logger.info("=== AI MODE: Starting LLM parameter extraction + AI summarization processing ===")
        
        # Check query relevance up front
        current_app.logger.info("🔍 AI MODE: Checking query relevance...")
        relevance_start = time.time()
        
        try:
            from search_api.services.generation.factories import QueryValidatorFactory
            relevance_checker = QueryValidatorFactory.create_validator()
            relevance_result = relevance_checker.validate_query_relevance(query)
            
            relevance_time = round((time.time() - relevance_start) * 1000, 2)
            metrics["relevance_check_time_ms"] = relevance_time
            metrics["query_relevance"] = relevance_result
            
            current_app.logger.info(f"🔍 AI MODE: Relevance check completed in {relevance_time}ms: {relevance_result}")
            
            # Handle non-EAO queries
            if not relevance_result.get("is_relevant", True):
                current_app.logger.info("🔍 AI MODE: Query not relevant to EAO - returning early")
                metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
                
                return {
                    "result": {
                        "response": relevance_result.get("response", "This query appears to be outside the scope of EAO's mandate."),
                        "documents": [],
                        "document_chunks": [],
                        "metrics": metrics,
                        "search_quality": "not_applicable",
                        "project_inference": {},
                        "document_type_inference": {},
                        "early_exit": True,
                        "exit_reason": "query_not_relevant"
                    }
                }
                
        except Exception as e:
            current_app.logger.error(f"🔍 AI MODE: Relevance check failed: {e}")
            metrics["relevance_check_time_ms"] = round((time.time() - relevance_start) * 1000, 2)
            metrics["query_relevance"] = {"checked": False, "error": str(e)}
        
        # LLM parameter extraction
        current_app.logger.info("🤖 AI MODE: Starting parameter extraction...")
        try:
            from search_api.services.generation.factories import ParameterExtractorFactory
            from search_api.clients.vector_search_client import VectorSearchClient
            
            agentic_start = time.time()
            current_app.logger.info("🤖 LLM: Starting parameter extraction from generation package...")
            
            # Fetch available options to provide context to the LLM
            current_app.logger.info("🤖 LLM: Fetching available options for context...")
            
            try:
                # Get available projects from vector search API (pass array directly)
                available_projects = VectorSearchClient.get_projects_list()
                
                current_app.logger.info(f"🤖 LLM: Found {len(available_projects) if available_projects else 0} available projects")
                
            except Exception as e:
                current_app.logger.warning(f"🤖 LLM: Could not fetch projects: {e}")
                available_projects = []
            
            try:
                # Get available document types from vector search API (pass array directly)
                available_document_types = VectorSearchClient.get_document_types()
                
                current_app.logger.info(f"🤖 LLM: Found {len(available_document_types) if available_document_types else 0} document types")
                
            except Exception as e:
                current_app.logger.warning(f"🤖 LLM: Could not fetch document types: {e}")
                available_document_types = []
            
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
                available_projects=available_projects,  # Now passing arrays directly
                available_document_types=available_document_types,  # Now passing arrays directly
                available_strategies=available_strategies,
                supplied_project_ids=project_ids if project_ids else None,
                supplied_document_type_ids=document_type_ids if document_type_ids else None,
                supplied_search_strategy=search_strategy if search_strategy else None,
                user_location=user_location,
                supplied_location=location if location else None,
                supplied_project_status=project_status if project_status else None,
                supplied_years=years if years else None
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
                
            # Apply extracted temporal parameters if not already provided
            if not location and extraction_result.get('location'):
                location = extraction_result['location']
                current_app.logger.info(f"🤖 LLM: Extracted location: {location}")
                
            if not project_status and extraction_result.get('project_status'):
                project_status = extraction_result['project_status']
                current_app.logger.info(f"🤖 LLM: Extracted project status: {project_status}")
                
            if not years and extraction_result.get('years'):
                years = extraction_result['years']
                current_app.logger.info(f"🤖 LLM: Extracted years: {years}")
            
            # Record metrics - use extraction_sources to determine what was actually extracted by AI
            metrics["ai_processing_time_ms"] = round((time.time() - agentic_start) * 1000, 2)
            metrics["ai_extraction"] = extraction_result
            
            # Check if AI actually extracted these parameters (vs supplied or fallback)
            extraction_sources = extraction_result.get('extraction_sources', {})
            metrics["ai_project_extraction"] = extraction_sources.get('project_ids') in ['llm_extracted', 'llm_sequential', 'llm_parallel']
            metrics["ai_document_type_extraction"] = extraction_sources.get('document_type_ids') in ['llm_extracted', 'llm_sequential', 'llm_parallel']
            metrics["ai_location_extraction"] = extraction_sources.get('location') in ['llm_extracted', 'llm_sequential', 'llm_parallel']
            metrics["ai_project_status_extraction"] = extraction_sources.get('project_status') in ['llm_extracted', 'llm_sequential', 'llm_parallel']
            metrics["ai_years_extraction"] = extraction_sources.get('years') in ['llm_extracted', 'llm_sequential', 'llm_parallel']
            metrics["ai_semantic_query_generated"] = semantic_query != query
            metrics["ai_extraction_confidence"] = extraction_result.get('confidence', 0.0)
            metrics["ai_extraction_provider"] = ParameterExtractorFactory.get_provider()
            
            # Add extraction summary for clarity
            extraction_sources = extraction_result.get('extraction_sources', {})
            metrics["agentic_extraction_summary"] = {
                "llm_calls_made": sum(1 for source in extraction_sources.values() if source in ["llm_extracted", "llm_sequential", "llm_parallel"]),
                "parameters_supplied": sum(1 for source in extraction_sources.values() if source == "supplied"),
                "parameters_extracted": sum(1 for source in extraction_sources.values() if source in ["llm_extracted", "llm_sequential", "llm_parallel"]),
                "parameters_fallback": sum(1 for source in extraction_sources.values() if source == "fallback")
            }
            
            current_app.logger.info(f"🤖 LLM: Parameter extraction completed in {metrics['ai_processing_time_ms']}ms using {ParameterExtractorFactory.get_provider()} (confidence: {extraction_result.get('confidence', 0.0)})")
            
        except Exception as e:
            current_app.logger.error(f"🤖 LLM: Error during parameter extraction: {e}")
            metrics["ai_error"] = str(e)
            metrics["ai_processing_time_ms"] = round((time.time() - agentic_start) * 1000, 2) if 'agentic_start' in locals() else 0
            semantic_query = query  # Fallback to original query
        
        # Handle parameter stuffing - user-provided parameters take precedence
        final_location = location  # User-provided takes precedence
        final_project_status = project_status  # User-provided takes precedence  
        final_years = years  # User-provided takes precedence
        
        # AI mode uses only LLM-extracted parameters (no pattern-based fallback)
        current_app.logger.info("🎯 AI MODE: Using LLM-extracted parameters (no pattern-based fallback)")
        current_app.logger.info(f"🎯 AI MODE: Final parameters - location: {final_location}, status: {final_project_status}, years: {final_years}")
        
        # Execute vector search with optimized parameters
        current_app.logger.info("🔍 AI MODE: Executing vector search...")
        search_result = cls._execute_vector_search(
            query, project_ids, document_type_ids, inference, ranking, 
            search_strategy, semantic_query, metrics, final_location, 
            final_project_status, final_years
        )
        
        # Check if search returned no results
        if not search_result["documents_or_chunks"]:
            current_app.logger.warning("🔍 AI MODE: No documents found")
            metrics["total_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return {
                "result": {
                    "response": "No relevant information found.",
                    "documents": [],
                    "document_chunks": [],
                    "metrics": metrics,
                    "search_quality": search_result["search_quality"],
                    "project_inference": search_result["project_inference"],
                    "document_type_inference": search_result["document_type_inference"]
                }
            }
        
        # Generate AI summary of search results
        current_app.logger.info("🔍 AI MODE: Generating AI summary...")
        summary_result = cls._generate_agentic_summary(search_result["documents_or_chunks"], query, metrics)
        
        # Handle summary generation errors
        if isinstance(summary_result, dict) and "error" in summary_result:
            current_app.logger.error("🔍 AI MODE: AI summary generation failed")
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
        
        current_app.logger.info("=== AI MODE: Processing completed ===")
        
        # Separate documents and document_chunks for consistent API response
        response_documents = []
        response_document_chunks = []
        
        # Categorize the search results based on their content
        for item in search_result["documents_or_chunks"]:
            if isinstance(item, dict):
                # Check if this looks like a document chunk (has chunk-specific fields)
                if any(field in item for field in ['chunk_text', 'chunk_content', 'content', 'chunk_id']):
                    response_document_chunks.append(item)
                else:
                    # Treat as document metadata
                    response_documents.append(item)
            else:
                response_documents.append(item)
        
        current_app.logger.info(f"📊 AI MODE: Categorized {len(response_documents)} documents and {len(response_document_chunks)} document chunks")

        return {
            "result": {
                "response": summary_result.get("response", "No response generated"),
                "documents": response_documents,
                "document_chunks": response_document_chunks,
                "metrics": metrics,
                "search_quality": search_result["search_quality"],
                "project_inference": search_result["project_inference"],
                "document_type_inference": search_result["document_type_inference"]
            }
        }