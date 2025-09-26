"""
RAG Handler

Handles basic RAG mode processing - direct retrieval with pattern-based temporal extraction.
"""
import time
from typing import Dict, List, Optional, Any
from flask import current_app

from .base_handler import BaseSearchHandler


class RAGHandler(BaseSearchHandler):
    """Handler for RAG mode processing - direct retrieval without summarization."""
    
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
        """Handle RAG mode processing - direct retrieval without summarization.
        
        RAG mode performs:
        - Query relevance check up front
        - Generic parameter extraction for location, project status, and years
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
            location: Optional location parameter (user-provided takes precedence)
            project_status: Optional project status parameter (user-provided takes precedence)
            years: Optional years parameter (user-provided takes precedence)
            
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
        
        # Track user-provided parameters for visibility (similar to AI/Agent modes)
        metrics["user_provided_parameters"] = {
            "project_ids": project_ids if project_ids else None,
            "document_type_ids": document_type_ids if document_type_ids else None,
            "search_strategy": search_strategy if search_strategy else None,
            "location": location if location else None,
            "project_status": project_status if project_status else None,
            "years": years if years else None,
            "user_location": user_location if user_location else None
        }
        
        # Track parameter sources for consistency with AI/Agent modes
        metrics["parameter_sources"] = {
            "project_ids": "supplied" if project_ids else None,
            "document_type_ids": "supplied" if document_type_ids else None,
            "search_strategy": "supplied" if search_strategy else None,
            "location": "supplied" if location else None,
            "project_status": "supplied" if project_status else None,
            "years": "supplied" if years else None
        }
        
        # Handle parameter stuffing - user-provided parameters take precedence
        final_location = location  # User-provided takes precedence
        final_project_status = project_status  # User-provided takes precedence  
        final_years = years  # User-provided takes precedence
        
        # If user didn't provide parameters, extract from query using generic method
        if not any([location, project_status, years]):
            current_app.logger.info("🎯 RAG MODE: No user parameters provided, extracting from query...")
            extracted_params = cls._extract_search_parameters(query, user_location)
            
            # Only use extracted parameters if user didn't provide them
            if not final_location:
                final_location = extracted_params['location']
                if final_location:
                    metrics["parameter_sources"]["location"] = "pattern_extracted"
            if not final_project_status:
                final_project_status = extracted_params['project_status']
                if final_project_status:
                    metrics["parameter_sources"]["project_status"] = "pattern_extracted"
            if not final_years:
                final_years = extracted_params['years']
                if final_years:
                    metrics["parameter_sources"]["years"] = "pattern_extracted"
                
            current_app.logger.info(f"🎯 RAG MODE: Final parameters - location: {final_location}, status: {final_project_status}, years: {final_years}")
        else:
            current_app.logger.info("🎯 RAG MODE: Using user-provided parameters (no extraction needed)")
        
        # Update metrics with final parameters used
        metrics["final_parameters"] = {
            "project_ids": project_ids,
            "document_type_ids": document_type_ids,
            "search_strategy": search_strategy,
            "location": final_location,
            "project_status": final_project_status,
            "years": final_years
        }
        
        # Execute vector search with provided parameters
        current_app.logger.info("🔍 RAG MODE: Executing vector search...")
        semantic_query = None  # RAG mode doesn't modify the query
        
        search_result = cls._execute_vector_search(
            query, project_ids, document_type_ids, inference, ranking, 
            search_strategy, semantic_query, metrics, final_location, 
            final_project_status, final_years
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
    def _extract_search_parameters(cls, query: str, user_location: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract search parameters using pattern-based temporal extraction.
        
        Extracts location, project status, and years from the query using regex patterns.
        This is the pattern-based extraction used by RAG and Summary modes.
        
        Args:
            query: The search query to extract parameters from
            user_location: Optional user location context
            
        Returns:
            Dict containing extracted parameters with keys 'location', 'project_status', 'years'
        """
        import re
        from datetime import datetime
        
        extracted_params = {
            'location': None,
            'project_status': None,
            'years': []
        }
        
        current_year = datetime.now().year
        
        # Temporal pattern extraction - convert relative expressions to year lists
        temporal_patterns = [
            # Recently/lately (last 2-3 years)
            (r'\b(?:recently|lately)\b', [current_year-2, current_year-1, current_year]),
            
            # Last/past N years
            (r'\b(?:in the )?(?:last|past)\s+(\d+)\s+years?\b', lambda match: list(range(current_year - int(match.group(1)), current_year + 1))),
            (r'\b(?:in the )?(?:last|past)\s+(?:few|couple of|several)\s+years?\b', [current_year-3, current_year-2, current_year-1, current_year]),
            
            # Since year
            (r'\bsince\s+(\d{4})\b', lambda match: list(range(int(match.group(1)), current_year + 1))),
            
            # Year ranges
            (r'\b(?:from\s+)?(\d{4})\s+to\s+(\d{4})\b', lambda match: list(range(int(match.group(1)), int(match.group(2)) + 1))),
            (r'\b(?:between\s+)?(\d{4})\s+and\s+(\d{4})\b', lambda match: list(range(int(match.group(1)), int(match.group(2)) + 1))),
            
            # Single years
            (r'\bin\s+(\d{4})\b', lambda match: [int(match.group(1))]),
            (r'\b(\d{4})\b', lambda match: [int(match.group(1))]),  # Catch standalone years
        ]
        
        # Apply temporal patterns
        for pattern, year_mapping in temporal_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                if callable(year_mapping):
                    years_to_add = year_mapping(match)
                else:
                    years_to_add = year_mapping
                    
                extracted_params['years'].extend(years_to_add)
                current_app.logger.info(f"📅 Relative temporal extracted: '{match.group()}' -> {years_to_add}")
        
        # Remove duplicates and sort years
        if extracted_params['years']:
            extracted_params['years'] = sorted(list(set(extracted_params['years'])))
            current_app.logger.info(f"📅 Final extracted years: {extracted_params['years']}")
        
        # Location detection - identify location references and use user location data
        location_keywords = [
            'near me', 'my area', 'nearby', 'local', 'in my city', 'in my region',
            'around here', 'close to me', 'in the vicinity', 'my location', 'my current location'
        ]
        
        query_lower = query.lower()
        for keyword in location_keywords:
            if keyword in query_lower:
                if user_location:
                    extracted_params['location'] = user_location
                    current_app.logger.info(f"📍 Location detected: found '{keyword}', using user location data")
                    break
                else:
                    current_app.logger.info(f"📍 Location reference detected ('{keyword}') but no user location available")
        
        # Project status extraction
        status_patterns = [
            (r'\b(active|ongoing|current)\s+(projects?|developments?)\b', 'active'),
            (r'\b(completed|finished|done)\s+(projects?|developments?)\b', 'completed'),
            (r'\b(planned|future|upcoming)\s+(projects?|developments?)\b', 'planned'),
            (r'\b(cancelled|canceled|terminated)\s+(projects?|developments?)\b', 'cancelled'),
            (r'\b(on\s+hold|paused|suspended)\s+(projects?|developments?)\b', 'on_hold')
        ]
        
        for pattern, status in status_patterns:
            if re.search(pattern, query_lower):
                extracted_params['project_status'] = status
                current_app.logger.info(f"📊 Project status extracted: {status}")
                break
        
        return extracted_params