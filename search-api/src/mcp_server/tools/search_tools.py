"""Search tools for MCP server.

These tools expose the vector search API's search capabilities to LLM agents,
including vector search, similarity search, and document retrieval.
"""

from typing import Any, Dict, List
import httpx
import logging
from datetime import datetime

from mcp.types import Tool

class SearchTools:
    """Handler for search-related MCP tools."""
    
    def __init__(self, http_client: httpx.AsyncClient, vector_api_base_url: str):
        """Initialize search tools with HTTP client and API base URL."""
        self.http_client = http_client
        self.vector_api_base_url = vector_api_base_url
        self.logger = logging.getLogger(__name__)
        
        # Cache for dynamic mappings (expires after 1 hour)
        self._project_mappings_cache = None
        self._project_mappings_cache_time = None
        self._doc_type_mappings_cache = None
        self._doc_type_mappings_cache_time = None
        self._search_strategies_cache = None
        self._search_strategies_cache_time = None
        
        # Import datetime here to avoid issues
        from datetime import timedelta
        self._cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def get_tools(self) -> List[Tool]:
        """Get list of available search tools."""
        return [
            Tool(
                name="suggest_filters",
                description="Analyze a query and suggest optimal project and document type filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's search query to analyze for filter suggestions"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about what the user is looking for"
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "default": 0.6,
                            "description": "Minimum confidence level for filter suggestions"
                        }
                    },
                    "required": ["query"]
                }
            ),
            
            Tool(
                name="get_available_projects",
                description="Get list of available projects for filtering search results",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters needed - returns all available projects"
                }
            ),
            
            Tool(
                name="get_available_document_types",
                description="Get list of available document types for filtering search results",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "description": "No parameters needed - returns all document types with metadata and aliases"
                }
            ),
            
            Tool(
                name="suggest_search_strategy",
                description="Analyze a query and suggest the optimal search strategy",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's search query to analyze for strategy recommendations"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about what the user is looking for"
                        },
                        "user_intent": {
                            "type": "string",
                            "enum": ["find_documents", "explore_topic", "get_overview", "specific_lookup", "find_similar"],
                            "default": "find_documents",
                            "description": "The user's intent to help optimize strategy selection"
                        }
                    },
                    "required": ["query"]
                }
            ),
            
            Tool(
                name="check_query_relevance",
                description="Check if a query is relevant to EAO (Environmental Assessment Office) and environmental assessments",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user's query to check for EAO relevance"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about the query"
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
    
    async def _get_dynamic_project_mappings(self) -> dict:
        """Fetch project mappings dynamically from the vector API with caching."""
        # Check if cache is valid
        if (self._project_mappings_cache is not None and 
            self._project_mappings_cache_time is not None and
            datetime.now() - self._project_mappings_cache_time < self._cache_duration):
            self.logger.info("Using cached project mappings")
            return self._project_mappings_cache
        
        try:
            self.logger.info("Fetching fresh project mappings from vector API")
            
            # Direct HTTP call to vector API instead of using VectorSearchClient
            # which requires Flask app context
            vector_search_url = f"{self.vector_api_base_url}/tools/projects"
            self.logger.info(f"Calling projects API: {vector_search_url}")
            
            response = await self.http_client.get(vector_search_url, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            projects = data.get('projects', [])
            mappings = {}
            
            for project in projects:
                project_id = project.get('project_id', '')
                project_name = project.get('project_name', '').lower().strip()
                
                if project_id and project_name:
                    # Add the exact project name
                    mappings[project_name] = project_id
                                
            # Update cache
            self._project_mappings_cache = mappings
            self._project_mappings_cache_time = datetime.now()
            
            self.logger.info(f"Loaded and cached {len(mappings)} project mappings from vector API")
            return mappings
            
        except Exception as e:
            self.logger.error(f"Failed to fetch dynamic project mappings: {e}")
            
            # If we have stale cache, use it
            if self._project_mappings_cache is not None:
                self.logger.warning("Using stale cached project mappings due to API error")
                return self._project_mappings_cache
            
            # No cache available, return empty dict
            self.logger.error("No project mappings available - API failed and no cache exists")
            return {}
    
    async def _get_dynamic_document_type_mappings(self) -> dict:
        """Fetch document type mappings dynamically from the vector API with caching."""
        # Check if cache is valid
        if (self._doc_type_mappings_cache is not None and 
            self._doc_type_mappings_cache_time is not None and
            datetime.now() - self._doc_type_mappings_cache_time < self._cache_duration):
            self.logger.info("Using cached document type mappings")
            return self._doc_type_mappings_cache
        
        try:
            self.logger.info("Fetching fresh document type mappings from vector API")
            
            # Direct HTTP call to vector API instead of using VectorSearchClient
            vector_search_url = f"{self.vector_api_base_url}/tools/document-types"
            self.logger.info(f"Calling document types API: {vector_search_url}")
            
            response = await self.http_client.get(vector_search_url, timeout=30.0)
            response.raise_for_status()
            
            doc_types_response = response.json()
            mappings = {}
            
            if doc_types_response and "document_types" in doc_types_response:
                document_types = doc_types_response["document_types"]
                
                for type_id, type_info in document_types.items():
                    type_name = type_info.get('name', '').lower()
                    aliases = type_info.get('aliases', [])
                    
                    if type_name:
                        # Map the main name to this type ID (avoid duplicates)
                        if type_name not in mappings:
                            mappings[type_name] = []
                        if type_id not in mappings[type_name]:
                            mappings[type_name].append(type_id)
                        
                        # Map all aliases to this type ID (avoid duplicates)
                        for alias in aliases:
                            alias_lower = alias.lower().strip()
                            if alias_lower and alias_lower not in mappings:
                                mappings[alias_lower] = []
                            if alias_lower and type_id not in mappings[alias_lower]:
                                mappings[alias_lower].append(type_id)
            
            # Update cache
            self._doc_type_mappings_cache = mappings
            self._doc_type_mappings_cache_time = datetime.now()
            
            self.logger.info(f"Loaded and cached document type mappings for {len(mappings)} keywords from vector API")
            return mappings
            
        except Exception as e:
            self.logger.error(f"Failed to fetch dynamic document type mappings: {e}")
            
            # If we have stale cache, use it
            if self._doc_type_mappings_cache is not None:
                self.logger.warning("Using stale cached document type mappings due to API error")
                return self._doc_type_mappings_cache
            
            # No cache available, return empty dict
            self.logger.error("No document type mappings available - API failed and no cache exists")
            return {}
    
    async def _get_dynamic_search_strategies_mappings(self) -> dict:
        """Fetch search strategies dynamically from the vector API with caching."""
        # Check if cache is valid
        if (self._search_strategies_cache is not None and 
            self._search_strategies_cache_time is not None and
            datetime.now() - self._search_strategies_cache_time < self._cache_duration):
            self.logger.info("Using cached search strategies mappings")
            return self._search_strategies_cache
        
        try:
            self.logger.info("Fetching fresh search strategies mappings from vector API")
            
            # Direct HTTP call to vector API
            vector_search_url = f"{self.vector_api_base_url}/tools/search-strategies"
            self.logger.info(f"Calling search strategies API: {vector_search_url}")
            
            response = await self.http_client.get(vector_search_url, timeout=30.0)
            response.raise_for_status()
            
            strategies_data = response.json()
            self.logger.info(f"Retrieved search strategies: {list(strategies_data.get('search_strategies', {}).keys())}")
            
            # Cache the result
            self._search_strategies_cache = strategies_data
            self._search_strategies_cache_time = datetime.now()
            
            return strategies_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch search strategies from vector API: {str(e)}")
            
            # Return cached data if available, even if expired
            if self._search_strategies_cache is not None:
                self.logger.warning("Using expired search strategies cache due to API failure")
                return self._search_strategies_cache
            
            # No cache available, return empty dict
            self.logger.error("No search strategies mappings available - API failed and no cache exists")
            return {}

    def clear_mappings_cache(self):
        """Clear the cached mappings to force fresh fetch from vector API."""
        self._project_mappings_cache = None
        self._project_mappings_cache_time = None
        self._doc_type_mappings_cache = None
        self._doc_type_mappings_cache_time = None
        self._search_strategies_cache = None
        self._search_strategies_cache_time = None
        self.logger.info("Cleared dynamic mappings cache")
    
    def get_cache_status(self) -> dict:
        """Get information about the current cache status."""
        now = datetime.now()
        status = {
            "project_mappings": {
                "cached": self._project_mappings_cache is not None,
                "cache_time": self._project_mappings_cache_time.isoformat() if self._project_mappings_cache_time else None,
                "is_fresh": (
                    self._project_mappings_cache_time is not None and 
                    now - self._project_mappings_cache_time < self._cache_duration
                ) if self._project_mappings_cache_time else False,
                "entries_count": len(self._project_mappings_cache) if self._project_mappings_cache else 0
            },
            "document_type_mappings": {
                "cached": self._doc_type_mappings_cache is not None,
                "cache_time": self._doc_type_mappings_cache_time.isoformat() if self._doc_type_mappings_cache_time else None,
                "is_fresh": (
                    self._doc_type_mappings_cache_time is not None and 
                    now - self._doc_type_mappings_cache_time < self._cache_duration
                ) if self._doc_type_mappings_cache_time else False,
                "entries_count": len(self._doc_type_mappings_cache) if self._doc_type_mappings_cache else 0
            },
            "search_strategies_mappings": {
                "cached": self._search_strategies_cache is not None,
                "cache_time": self._search_strategies_cache_time.isoformat() if self._search_strategies_cache_time else None,
                "is_fresh": (
                    self._search_strategies_cache_time is not None and 
                    now - self._search_strategies_cache_time < self._cache_duration
                ) if self._search_strategies_cache_time else False,
                "entries_count": len(self._search_strategies_cache.get('search_strategies', {})) if self._search_strategies_cache else 0
            },
            "cache_duration_hours": self._cache_duration.total_seconds() / 3600
        }
        return status
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls for search operations."""
        if name == "suggest_filters":
            return await self._suggest_filters(arguments)
        elif name == "get_available_projects":
            return await self._get_available_projects(arguments)
        elif name == "get_available_document_types":
            return await self._get_available_document_types(arguments)
        elif name == "suggest_search_strategy":
            return await self._suggest_search_strategy(arguments)
        elif name == "check_query_relevance":
            return await self._check_query_relevance(arguments)
        else:
            raise ValueError(f"Unknown search tool: {name}")

    async def _get_available_projects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available projects using the Vector API tools endpoint."""
        try:
            self.logger.info("Fetching available projects from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/projects"
            )
            response.raise_for_status()
            
            projects_response = response.json()
            
            # Extract projects from the response structure: {"projects": [...]}
            projects = projects_response.get("projects", [])
            
            result = {
                "tool": "get_available_projects",
                "projects": projects,
                "total_projects": len(projects),
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            self.logger.info(f"Retrieved {result['total_projects']} projects")
            return result
            
        except Exception as e:
            self.logger.error(f"Get available projects error: {str(e)}")
            return {
                "tool": "get_available_projects",
                "error": str(e),
                "parameters": args
            }

    async def _get_available_document_types(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available document types using the Vector API tools endpoint."""
        try:
            self.logger.info("Fetching available document types from Vector API")
            
            response = await self.http_client.get(
                f"{self.vector_api_base_url}/tools/document-types"
            )
            response.raise_for_status()
            
            doc_types_response = response.json()
            
            # Extract document_types from the response structure: {"document_types": {...}}
            doc_types_dict = doc_types_response.get("document_types", {})
            
            # Convert the dictionary format to a list for easier LLM consumption
            document_types = []
            for doc_type_id, doc_type_info in doc_types_dict.items():
                document_types.append({
                    "document_type_id": doc_type_id,
                    "name": doc_type_info.get("name", ""),
                    "aliases": doc_type_info.get("aliases", [])
                })
            
            result = {
                "tool": "get_available_document_types",
                "document_types": document_types,
                "raw_response": doc_types_dict,  # Keep original format for reference
                "total_document_types": len(document_types),
                "metadata": {
                    "source": "vector_api_tools_endpoint",
                    "timestamp": "2025-08-18T00:00:00Z"
                }
            }
            
            self.logger.info(f"Retrieved {result['total_document_types']} document types")
            return result
            
        except Exception as e:
            self.logger.error(f"Get available document types error: {str(e)}")
            return {
                "tool": "get_available_document_types",
                "error": str(e),
                "parameters": args
            }

    async def _suggest_filters(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query and suggest optimal filters using LLM intelligence."""
        try:
            query = args["query"]
            context = args.get("context", "")
            confidence_threshold = args.get("confidence_threshold", 0.6)
            
            self.logger.info(f"Analyzing query for filter suggestions using LLM: {query}")
            
            # Use LLM analysis without requiring Vector API metadata
            filter_suggestions = await self._analyze_query_with_llm(query, context)
            
            # Build comprehensive response
            suggestions = {
                "tool": "suggest_filters",
                "query": query,
                "context": context,
                "confidence_threshold": confidence_threshold,
                "suggested_filters": filter_suggestions.get("suggested_filters", {}),
                "confidence": filter_suggestions.get("confidence", 0.8),
                "entities_detected": filter_suggestions.get("entities_detected", []),
                "recommendations": filter_suggestions.get("recommendations", []),
                "reasoning": filter_suggestions.get("explanation", "Filters suggested using LLM analysis"),
                "status": "llm_analysis_complete",
                "llm_used": True
            }
            
            # Add search strategy recommendation based on analysis
            if filter_suggestions.get("suggested_filters"):
                suggestions["recommended_search_strategy"] = "HYBRID_SEMANTIC_FALLBACK"
            else:
                suggestions["recommended_search_strategy"] = "SEMANTIC_ONLY"
            
            self.logger.info(f"LLM filter analysis complete: {suggestions['confidence']} confidence")
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Suggest filters error: {str(e)}")
            # Fallback to simple rule-based analysis
            return await self._simple_fallback_filter_analysis(args)

    async def _suggest_search_strategy(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a query and suggest the optimal search strategy using LLM analysis."""
        try:
            query = args["query"]
            context = args.get("context", "")
            user_intent = args.get("user_intent", "find_documents")
            
            self.logger.info(f"Analyzing query for search strategy: {query}")
            
            # Get available search strategies from the vector API
            strategies_data = await self._get_dynamic_search_strategies_mappings()
            available_strategies = strategies_data.get("search_strategies", {})
            
            if not available_strategies:
                self.logger.warning("No search strategies available from API, using fallback")
                return {
                    "tool": "suggest_search_strategy",
                    "query": query,
                    "recommended_strategy": "HYBRID_SEMANTIC_FALLBACK",
                    "confidence": 0.5,
                    "explanation": "Fallback strategy - could not retrieve available strategies from API"
                }
            
            # Use LLM to analyze the query and recommend strategy
            strategy_analysis = await self._analyze_query_for_strategy(query, context, user_intent, available_strategies)
            
            return {
                "tool": "suggest_search_strategy",
                "query": query,
                "user_intent": user_intent,
                "recommended_strategy": strategy_analysis.get("recommended_strategy", "HYBRID_SEMANTIC_FALLBACK"),
                "confidence": strategy_analysis.get("confidence", 0.7),
                "explanation": strategy_analysis.get("explanation", "Strategy selected based on query analysis"),
                "available_strategies": list(available_strategies.keys()),
                "alternative_strategies": strategy_analysis.get("alternatives", [])
            }
            
        except Exception as e:
            self.logger.error(f"Suggest search strategy error: {str(e)}")
            # Fallback to default strategy
            return {
                "tool": "suggest_search_strategy",
                "query": args.get("query", ""),
                "recommended_strategy": "HYBRID_SEMANTIC_FALLBACK",
                "confidence": 0.5,
                "explanation": f"Fallback strategy due to error: {str(e)}",
                "error": str(e)
            }

    async def _analyze_query_for_strategy(self, query: str, context: str, user_intent: str, available_strategies: dict) -> dict:
        """Use LLM to analyze query characteristics and recommend optimal search strategy."""
        try:
            # Build prompt for LLM strategy analysis
            strategy_list = "\n".join([f"- {name}: {info.get('description', 'No description')}" 
                                     for name, info in available_strategies.items()])
            
            llm_prompt = f"""Analyze this search query and recommend the optimal search strategy.

Query: "{query}"
Context: {context}
User Intent: {user_intent}

Available Search Strategies:
{strategy_list}

Consider these factors:
1. Query specificity (exact terms vs broad concepts)
2. Expected document types 
3. User intent (find specific docs vs explore topic)
4. Query complexity (simple terms vs complex phrases)
5. Generic document requests (asking for "all" documents of a type)

Strategy Guidelines:
- EXACT_MATCH: For specific IDs, codes, or precise terms
- KEYWORD_ONLY: For simple keyword searches, specific terminology  
- SEMANTIC_ONLY: For conceptual searches, natural language questions
- DOCUMENT_ONLY: For generic document requests like "all correspondence", "all reports", "I want all documents"
- HYBRID_SEMANTIC_FALLBACK: For general searches needing both precision and recall
- HYBRID_KEYWORD_FALLBACK: For searches with mix of specific and general terms
- HYBRID_PARALLEL: When you need comprehensive results with multiple approaches

IMPORTANT: Use DOCUMENT_ONLY when the query contains patterns like:
- "all the [document_type]" (e.g., "all the correspondence")
- "I want all [document_type]" (e.g., "I want all reports")
- "give me all [document_type]" or similar broad requests
- Generic requests for document types without specific content criteria

Respond with ONLY a JSON object:
{{
  "recommended_strategy": "STRATEGY_NAME",
  "confidence": 0.8,
  "explanation": "Brief explanation of why this strategy is optimal",
  "alternatives": ["ALTERNATIVE_STRATEGY1", "ALTERNATIVE_STRATEGY2"]
}}"""

            # Use the same LLM synthesis approach as suggest_filters
            from search_api.services.synthesizer_resolver import SynthesizerResolver
            synthesizer = SynthesizerResolver.get_synthesizer()
            
            self.logger.info("Calling LLM for search strategy analysis")
            llm_response = synthesizer.query_llm(llm_prompt)
            
            if isinstance(llm_response, dict) and 'response' in llm_response:
                response_text = llm_response['response']
            elif isinstance(llm_response, str):
                response_text = llm_response
            else:
                response_text = str(llm_response)
            
            # Parse LLM response
            return await self._extract_strategy_from_llm_text(response_text, query, available_strategies)
            
        except Exception as e:
            self.logger.error(f"Error in LLM strategy analysis: {str(e)}")
            # Return rule-based fallback
            return await self._rule_based_strategy_selection(query, user_intent, available_strategies)

    async def _extract_strategy_from_llm_text(self, response_text: str, query: str, available_strategies: dict) -> dict:
        """Extract strategy recommendation from LLM response text."""
        try:
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                # Validate the recommended strategy exists
                recommended = parsed.get("recommended_strategy", "HYBRID_SEMANTIC_FALLBACK")
                if recommended not in available_strategies:
                    self.logger.warning(f"LLM recommended unknown strategy {recommended}, falling back to HYBRID_SEMANTIC_FALLBACK")
                    recommended = "HYBRID_SEMANTIC_FALLBACK"
                
                return {
                    "recommended_strategy": recommended,
                    "confidence": float(parsed.get("confidence", 0.7)),
                    "explanation": parsed.get("explanation", "Strategy recommended by LLM analysis"),
                    "alternatives": parsed.get("alternatives", [])
                }
            
        except Exception as e:
            self.logger.warning(f"Could not parse LLM strategy response: {str(e)}")
        
        # Fallback to rule-based analysis
        return await self._rule_based_strategy_selection(query, "find_documents", available_strategies)

    async def _rule_based_strategy_selection(self, query: str, user_intent: str, available_strategies: dict) -> dict:
        """Rule-based fallback for strategy selection when LLM fails."""
        query_lower = query.lower()
        
        # Check for generic document requests (should use DOCUMENT_ONLY)
        generic_document_patterns = [
            'all the', 'all documents', 'all correspondence', 'all reports', 'all files',
            'want all', 'need all', 'get all', 'find all', 'show all', 'give me all',
            'i want all', 'i need all', 'all of the', 'everything', 'any documents',
            'any correspondence', 'any reports', 'any files'
        ]
        
        document_type_keywords = [
            'correspondence', 'reports', 'documents', 'files', 'memos', 'letters',
            'emails', 'communications', 'records', 'submissions', 'applications'
        ]
        
        # Check if this is a generic document request
        is_generic_request = False
        has_document_type = any(doc_type in query_lower for doc_type in document_type_keywords)
        has_generic_pattern = any(pattern in query_lower for pattern in generic_document_patterns)
        
        if has_generic_pattern and has_document_type:
            is_generic_request = True
        elif any(f"all {doc_type}" in query_lower for doc_type in document_type_keywords):
            is_generic_request = True
        elif any(f"want {doc_type}" in query_lower for doc_type in document_type_keywords):
            is_generic_request = True
        
        # Strategy selection logic
        if any(pattern in query_lower for pattern in ['id:', 'number:', 'code:', '#']):
            recommended = "EXACT_MATCH" if "EXACT_MATCH" in available_strategies else "KEYWORD_ONLY"
            explanation = "Detected specific identifiers, using exact/keyword matching"
        elif is_generic_request:
            recommended = "DOCUMENT_ONLY" if "DOCUMENT_ONLY" in available_strategies else "HYBRID_SEMANTIC_FALLBACK"
            explanation = "Detected generic document request, using document-focused search"
        elif user_intent == "specific_lookup":
            recommended = "KEYWORD_ONLY" if "KEYWORD_ONLY" in available_strategies else "HYBRID_KEYWORD_FALLBACK"
            explanation = "Specific lookup intent, prioritizing keyword matching"
        elif user_intent in ["explore_topic", "get_overview"]:
            recommended = "SEMANTIC_ONLY" if "SEMANTIC_ONLY" in available_strategies else "HYBRID_SEMANTIC_FALLBACK"
            explanation = "Exploratory intent, using semantic search for broader results"
        elif len(query.split()) <= 2:
            recommended = "KEYWORD_ONLY" if "KEYWORD_ONLY" in available_strategies else "HYBRID_KEYWORD_FALLBACK"
            explanation = "Short query, using keyword-focused approach"
        else:
            recommended = "HYBRID_SEMANTIC_FALLBACK"
            explanation = "General query, using hybrid approach for balanced results"
        
        # Ensure the strategy exists
        if recommended not in available_strategies:
            recommended = "HYBRID_SEMANTIC_FALLBACK"
            explanation = "Fallback to default hybrid strategy"
            
        return {
            "recommended_strategy": recommended,
            "confidence": 0.6,
            "explanation": explanation,
            "alternatives": ["HYBRID_SEMANTIC_FALLBACK", "KEYWORD_ONLY"]
        }

    async def _analyze_query_with_llm(self, query: str, context: str = "") -> dict:
        """Use LLM to analyze query and suggest intelligent filters without external dependencies."""
        try:
            # Get dynamic mappings from vector API to build accurate LLM prompt
            project_mappings = await self._get_dynamic_project_mappings()
            doc_type_mappings = await self._get_dynamic_document_type_mappings()
            
            # Build project mappings section for LLM prompt
            project_mappings_text = ""
            if project_mappings:
                project_mappings_text = "## Project ID Mappings (use these exact IDs):\n"
                for project_name, project_id in project_mappings.items():
                    project_mappings_text += f"- {project_name.title()}: \"{project_id}\"\n"
            else:
                project_mappings_text = "## Project ID Mappings:\n- No projects available\n"
            
            # Build document type mappings section for LLM prompt
            doc_type_mappings_text = ""
            if doc_type_mappings:
                doc_type_mappings_text = "## Document Type ID Mappings (use these exact IDs):\n"
                # Group by document type IDs to show which keywords map to which IDs
                id_to_keywords = {}
                for keyword, ids in doc_type_mappings.items():
                    for doc_id in ids:
                        if doc_id not in id_to_keywords:
                            id_to_keywords[doc_id] = []
                        if keyword not in id_to_keywords[doc_id]:
                            id_to_keywords[doc_id].append(keyword)
                
                for doc_id, keywords in id_to_keywords.items():
                    keyword_list = "/".join([kw.title() for kw in keywords[:3]])  # Show first 3 keywords
                    doc_type_mappings_text += f"- {keyword_list}: \"{doc_id}\"\n"
            else:
                doc_type_mappings_text = "## Document Type ID Mappings:\n- No document types available\n"
            
            # Create a specialized prompt for filter suggestion and semantic query extraction
            filter_prompt = f"""# Task: Analyze search query and extract filters + clean semantic query

## Query to analyze:
"{query}"

## Context (if any):
{context}

{project_mappings_text}

{doc_type_mappings_text}

## Analysis Guidelines:
1. Extract project names and map to exact IDs above
2. Extract document types and map to exact IDs above
3. Use ONLY the verified IDs provided in the mappings above
4. Generate a clean semantic query by removing:
   - Project names that were extracted as filters
   - Document types that were extracted as filters
   - Common stop words (the, a, an, for, about, etc.)
   - Query structure words (find me, show me, what are, etc.)
   - Keep only the core semantic content for search

## Examples:
Query: "Find me all letters about environmental impact"
- projectIds: [] (no specific project detected)
- documentTypeIds: [appropriate letter type IDs from mappings above]
- semanticQuery: "environmental impact"

Query: "What reports are available for [project name]?"
- projectIds: [appropriate project ID if found in mappings above]
- documentTypeIds: [appropriate report type IDs from mappings above]
- semanticQuery: "reports [project context]"
- semanticQuery: "environmental impacts nooaitch indian band"

## Response format (JSON only):
{{
    "suggested_filters": {{
        "projectIds": ["681a6e4e85cefd0022839a0e"], // only if project clearly mentioned
        "documentTypeIds": ["5cf00c03a266b7e1877504cb"], // only if document type clearly mentioned
        "semanticQuery": "clean search terms", // core content without stop words and extracted filter terms
        "searchStrategy": "HYBRID_SEMANTIC_FALLBACK"
    }},
    "entities_detected": ["entity1", "entity2"],
    "recommendations": ["Clear reasoning for each suggestion"],
    "confidence": 0.85
}}

## Important:
- semanticQuery should contain clean, searchable content
- Remove generic terms but keep important entities and concepts
- Be conservative with filter extraction
- Focus on accuracy over completeness"""
            
            # Get the synthesizer and query the LLM
            from search_api.services.synthesizer_resolver import get_synthesizer
            synthesizer = get_synthesizer()
            
            self.logger.info(f"Sending LLM prompt for query analysis: {query}")
            self.logger.info(f"LLM prompt (first 500 chars): {filter_prompt[:500]}...")
            
            llm_response = synthesizer.query_llm(filter_prompt)
            
            # Extract the response text
            if isinstance(llm_response, dict) and 'response' in llm_response:
                response_text = llm_response['response']
            else:
                response_text = str(llm_response)
            
            self.logger.info(f"LLM raw response: {response_text}")
            
            # Try to parse JSON from the response
            import re
            import json
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    analysis_result = json.loads(json_match.group(0))
                    self.logger.info(f"LLM analysis result parsed successfully: {analysis_result}")
                    
                    # Log specific components for debugging
                    suggested_filters = analysis_result.get('suggested_filters', {})
                    self.logger.info(f"LLM extracted projectIds: {suggested_filters.get('projectIds', [])}")
                    self.logger.info(f"LLM extracted documentTypeIds: {suggested_filters.get('documentTypeIds', [])}")
                    self.logger.info(f"LLM generated semanticQuery: '{suggested_filters.get('semanticQuery', '')}'")
                    
                    return analysis_result
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse LLM JSON response: {e}")
                    self.logger.error(f"Response text: {response_text}")
            
            # If LLM parsing fails, fall back to rule-based analysis
            self.logger.warning("LLM analysis failed, falling back to rule-based analysis")
            return await self._simple_rule_based_filter_analysis(query, context)
            
        except Exception as e:
            self.logger.error(f"LLM analysis error: {e}")
            # Fall back to rule-based analysis
            return await self._simple_rule_based_filter_analysis(query, context)

    async def _extract_analysis_from_llm_text(self, response_text: str, query: str) -> dict:
        """Extract filter suggestions from LLM text response using pattern matching with dynamic mappings."""
        suggested_filters = {}
        entities_detected = []
        recommendations = []
        
        # Get dynamic mappings from vector API
        project_mappings = await self._get_dynamic_project_mappings()
        
        # Look for project patterns
        for project_key, project_id in project_mappings.items():
            if project_key in query.lower() or project_key in response_text.lower():
                suggested_filters['projectIds'] = [project_id]
                entities_detected.append(project_key.title())
                recommendations.append(f"Detected {project_key.title()} project")
                break
        
        # Get dynamic document type mappings
        doc_type_mappings = await self._get_dynamic_document_type_mappings()
        
        # Look for document type patterns
        for doc_key, doc_ids in doc_type_mappings.items():
            if doc_key in query.lower() or doc_key in response_text.lower():
                suggested_filters['documentTypeIds'] = doc_ids
                recommendations.append(f"Detected document type: {doc_key}")
                break
        
        # Look for entity patterns
        entity_patterns = [
            'nooaitch indian band',
            'first nation',
            'indigenous',
            'band council'
        ]
        
        for pattern in entity_patterns:
            if pattern in query.lower() or pattern in response_text.lower():
                entities_detected.append(pattern.title())
                recommendations.append(f"Detected entity: {pattern.title()}")
        
        return {
            'suggested_filters': suggested_filters,
            'entities_detected': entities_detected,
            'recommendations': recommendations,
            'confidence': 0.7,
            'explanation': 'Filters extracted from LLM text response using dynamic mappings from vector API'
        }

    async def _simple_rule_based_filter_analysis(self, query: str, context: str = "") -> dict:
        """Simple rule-based filter analysis as fallback using dynamic mappings from vector API."""
        import re  # Import re at the beginning of the function
        
        suggested_filters = {}
        recommendations = []
        entities_detected = []
        query_lower = query.lower()
        
        # Get dynamic mappings from vector API
        project_mappings = await self._get_dynamic_project_mappings()
        document_type_mappings = await self._get_dynamic_document_type_mappings()
        
        # Enhanced project detection with tracking for semantic query cleaning
        detected_projects = []
        detected_project_phrases = []
        for project_key, project_id in project_mappings.items():
            if project_key in query_lower:
                detected_projects.append(project_id)
                detected_project_phrases.append(project_key)
                entities_detected.append(project_key.title())
                recommendations.append(f"Detected project: {project_key.title()}")
                break  # Take the first match to avoid duplicates
        
        if detected_projects:
            suggested_filters['projectIds'] = detected_projects
        
        # Enhanced document type detection with tracking for semantic query cleaning
        detected_doc_types = []
        detected_doc_phrases = []
        for doc_key, doc_ids in document_type_mappings.items():
            if doc_key in query_lower:
                # doc_ids is now an array, so extend the list
                detected_doc_types.extend(doc_ids)
                detected_doc_phrases.append(doc_key)
                recommendations.append(f"Detected document type: {doc_key}")
                break  # Take the first match to avoid duplicates
        
        if detected_doc_types:
            suggested_filters['documentTypeIds'] = detected_doc_types
        elif any(word in query_lower for word in ['permit', 'application', 'approval']):
            suggested_filters['documentTypeIds'] = ['permits']
            detected_doc_phrases.append('permit')
            recommendations.append("Detected permits/applications request")
        
        # Create semantic query by removing project and document type references
        semantic_query = query
        noise_phrases = []
        
        # Remove project mentions
        for phrase in detected_project_phrases:
            noise_phrases.extend([
                phrase,
                f"for the {phrase}",
                f"the {phrase}",
                f"{phrase} project",
                f"for {phrase}",
                f"in {phrase}",
                f"from {phrase}"
            ])
        
        # Remove document type mentions (including variations)
        for phrase in detected_doc_phrases:
            # Add both singular and plural forms, and common variations
            phrase_variations = [phrase]
            
            # Add plural/singular variations
            if phrase.endswith('s') and len(phrase) > 3:
                # Remove 's' for plural -> singular
                phrase_variations.append(phrase[:-1])
            elif not phrase.endswith('s'):
                # Add 's' for singular -> plural
                phrase_variations.append(phrase + 's')
            
            # Add common document type variations
            if 'letter' in phrase:
                phrase_variations.extend(['letter', 'letters', 'correspondence'])
            elif 'correspondence' in phrase:
                phrase_variations.extend(['correspondence', 'letter', 'letters'])
            elif 'report' in phrase:
                phrase_variations.extend(['report', 'reports', 'study', 'studies'])
            elif 'assessment' in phrase:
                phrase_variations.extend(['assessment', 'assessments', 'evaluation', 'evaluations'])
            
            # Add all variations to noise phrases
            for variation in phrase_variations:
                noise_phrases.extend([
                    variation,
                    f"all {variation}",
                    f"the {variation}",
                    f"any {variation}",
                    f"find {variation}",
                    f"get {variation}",
                    f"show {variation}",
                    f"i want all {variation}",
                    f"find me all {variation}",
                    f"show me {variation}",
                    f"get me {variation}",
                    f"about {variation}",
                    f"regarding {variation}"
                ])
        
        # Remove common query structure words, prepositions, and generic terms
        noise_phrases.extend([
            # Query structure words
            "for the", "i want", "find me", "show me", "get me", "that mention",
            "that include", "that contain", "related to", "about", "regarding",
            "what are", "what is", "how are", "how is", "where are", "where is",
            "tell me about", "give me", "provide", "search for", "look for",
            
            # Generic project-related terms
            "project", "projects", "project's", "projects'",
            "initiative", "initiatives", "program", "programs",
            "development", "developments", "proposal", "proposals"
        ])
        
        # Clean the semantic query
        semantic_query_lower = query_lower
        for phrase in sorted(noise_phrases, key=len, reverse=True):  # Remove longer phrases first
            # Use word boundaries to avoid partial word removal
            pattern = r'\b' + re.escape(phrase) + r'\b'
            semantic_query_lower = re.sub(pattern, '', semantic_query_lower)
        
        # Clean up extra spaces, punctuation, and remaining stop words
        semantic_query_clean = re.sub(r'\s+', ' ', semantic_query_lower).strip()
        semantic_query_clean = re.sub(r'^[,\s]+|[,\s]+$', '', semantic_query_clean)  # Remove leading/trailing commas and spaces
        semantic_query_clean = semantic_query_clean.strip('\'"')  # Remove quotes
        
        # Remove common stop words at word level
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'should', 'could', 'can', 'may', 'might', 'must', 'shall',
            'this', 'that', 'these', 'those', 'there', 'here', 'where', 'when', 'who', 'what', 'which', 'why', 'how',
            'all', 'any', 'some', 'many', 'much', 'most', 'more', 'less', 'few', 'several', 'both', 'each', 'every',
            'other', 'another', 'such', 'same', 'own', 'very', 'just', 'only', 'also', 'even', 'still', 'yet'
        }
        
        words = semantic_query_clean.split()
        cleaned_words = []
        for word in words:
            # Keep words that are not stop words, not single characters, and not just numbers
            clean_word = word.strip('.,!?;:()[]{}"\'-').lower()
            if (len(clean_word) > 1 and 
                clean_word not in stop_words and
                not clean_word.isdigit() and
                clean_word.isalpha()):  # Only keep alphabetic words
                cleaned_words.append(clean_word)
        
        semantic_query_clean = ' '.join(cleaned_words)
        
        # If semantic query is too short or empty, use original query
        if len(semantic_query_clean) < 3:
            semantic_query_clean = query
        
        # Add semantic query to suggested filters
        if semantic_query_clean and semantic_query_clean != query.lower():
            suggested_filters['semanticQuery'] = semantic_query_clean
            recommendations.append(f"Generated semantic query: '{semantic_query_clean}'")
        
        # Simple entity detection
        if 'nooaitch indian band' in query_lower:
            entities_detected.append("Nooaitch Indian Band")
            recommendations.append("Detected Nooaitch Indian Band entity")
        
        # Temporal analysis
        if any(term in query_lower for term in ['recent', 'latest', 'new', '2024', '2023', 'this year']):
            suggested_filters['dateRange'] = {
                'start_date': '2023-01-01',
                'end_date': '2024-12-31'
            }
            recommendations.append("Detected temporal reference - added recent date range")
        
        return {
            'suggested_filters': suggested_filters,
            'entities_detected': entities_detected,
            'recommendations': recommendations,
            'confidence': 0.6,
            'explanation': 'Filters suggested using simple rule-based analysis'
        }

    async def _simple_fallback_filter_analysis(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Complete fallback analysis when LLM fails."""
        query = args.get("query", "")
        context = args.get("context", "")
        
        fallback_result = await self._simple_rule_based_filter_analysis(query, context)
        
        return {
            "tool": "suggest_filters",
            "query": query,
            "suggested_filters": fallback_result.get("suggested_filters", {}),
            "confidence": fallback_result.get("confidence", 0.5),
            "entities_detected": fallback_result.get("entities_detected", []),
            "recommendations": fallback_result.get("recommendations", ["Using simple fallback analysis"]),
            "reasoning": fallback_result.get("explanation", "Simple fallback analysis used"),
            "status": "fallback_analysis_complete",
            "llm_used": False
        }

    def _extract_analysis_with_metadata(self, response_text: str, query: str, metadata: dict) -> dict:
        """Extract filter suggestions from LLM text response using regex with metadata validation."""
        suggested_filters = {}
        entities_detected = []
        recommendations = []
        
        # Extract project mentions and match against available projects
        available_projects = metadata.get("projects", [])
        for project in available_projects:
            if isinstance(project, dict):
                project_id = project.get("id", project.get("project_id", ""))
                project_name = project.get("name", project.get("project_name", ""))
                
                # Check if project is mentioned in response or query
                if (project_name and project_name.lower() in response_text.lower()) or \
                   (project_name and project_name.lower() in query.lower()):
                    if 'projectIds' not in suggested_filters:
                        suggested_filters['projectIds'] = []
                    suggested_filters['projectIds'].append(project_id)
                    entities_detected.append(project_name)
                    recommendations.append(f"Detected project: {project_name}")
        
        # Extract document type mentions and match against available types
        available_doc_types = metadata.get("document_types", [])
        for doc_type in available_doc_types:
            doc_type_id = doc_type.get("document_type_id", "")
            name = doc_type.get("name", "")
            aliases = doc_type.get("aliases", [])
            
            # Check all possible names/aliases
            all_names = [name] + aliases if name else aliases
            for check_name in all_names:
                if check_name and check_name.lower() in response_text.lower():
                    if 'documentTypeIds' not in suggested_filters:
                        suggested_filters['documentTypeIds'] = []
                    if doc_type_id not in suggested_filters['documentTypeIds']:
                        suggested_filters['documentTypeIds'].append(doc_type_id)
                        recommendations.append(f"Detected document type: {name} (matched: {check_name})")
        
        return {
            'suggested_filters': suggested_filters,
            'entities_detected': entities_detected,
            'recommendations': recommendations,
            'confidence': 0.7,
            'explanation': 'Filters extracted from LLM text response with metadata validation'
        }

    async def _check_query_relevance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a query is relevant to EAO and environmental assessments using LLM with rule-based fallback."""
        query = args.get("query", "")
        context = args.get("context", "")
        
        try:
            self.logger.info(f"Checking query relevance for: {query[:100]}...")
            
            # First, try LLM-based analysis
            try:
                return await self._llm_based_relevance_check(query, context)
            except Exception as llm_error:
                self.logger.warning(f"LLM-based relevance check failed: {llm_error}")
                self.logger.info("Falling back to enhanced rule-based relevance check")
                return await self._rule_based_relevance_check(query, context)
                
        except Exception as e:
            self.logger.error(f"Query relevance check error: {str(e)}")
            return {
                "tool": "check_query_relevance",
                "error": str(e),
                "query": query,
                "is_eao_relevant": True,  # Default to allowing the query in case of error
                "confidence": 0.0,
                "recommendation": "proceed_with_search",
                "reasoning": ["Error occurred during relevance check - defaulting to allow"]
            }

    async def _llm_based_relevance_check(self, query: str, context: str) -> Dict[str, Any]:
        """Use LLM to intelligently assess query relevance to EAO scope."""
        
        # Build context-rich prompt for LLM
        relevance_prompt = f"""You are an expert assistant for the Environmental Assessment Office (EAO) of British Columbia. Your job is to determine if a user's query is relevant to EAO scope and environmental assessments.

## EAO Context:
The EAO oversees environmental assessments for major projects in BC including:
- Mining, oil & gas, renewable energy projects
- Infrastructure (pipelines, transmission lines, highways)
- Industrial facilities (ports, terminals, waste management)
- Resort and tourism developments

EAO documents include environmental assessment reports, certificates, correspondence, consultation records, technical studies, and all supporting documentation for the assessment process.

## Query Analysis:
User Query: "{query}"
Additional Context: "{context if context else 'None provided'}"

## Your Task:
Analyze if this query is relevant to EAO scope. Consider:

1. **Direct EAO Relevance**: Contains environmental assessment terms, project types, or regulatory language
2. **Document Search Relevance**: Could be searching for specific documents, names, places, or terms that appear in EAO documents
3. **RAG Database Context**: Since this searches a database of EAO documents, even proper nouns, locations, company names, or technical terms could be relevant
4. **Short Query Handling**: Short queries might be specific search terms, project names, or document references

## Guidelines:
- **Allow RAG searches**: Proper nouns, locations, company names, technical terms could all appear in EAO documents
- **Be permissive**: When in doubt, allow the search - it's better to search and find nothing than to block a valid query
- **Block obvious non-EAO**: Only reject queries that are clearly about unrelated topics (sports, entertainment, personal matters, etc.)

Respond with ONLY a JSON object:
{{
  "is_eao_relevant": true/false,
  "confidence": 0.0-1.0,
  "reasoning": ["clear explanation of decision"],
  "recommendation": "proceed_with_search" or "inform_user_out_of_scope",
  "query_type": "environmental_assessment|document_search|proper_noun|technical_term|clearly_unrelated",
  "suggested_response": "only if recommending out_of_scope, provide helpful guidance"
}}"""

        # Get the synthesizer and query the LLM
        try:
            from search_api.services.synthesizer_resolver import SynthesizerResolver
            synthesizer = SynthesizerResolver.get_synthesizer()
            
            if not synthesizer:
                self.logger.warning("No synthesizer available for LLM relevance check")
                raise Exception("No synthesizer configured")
        except ImportError as e:
            self.logger.warning(f"Cannot import search_api modules: {e}")
            raise Exception("search_api modules not available")
        
        self.logger.info(f"Sending LLM prompt for query relevance analysis")
        self.logger.debug(f"LLM relevance prompt: {relevance_prompt[:500]}...")
        
        llm_response = synthesizer.query_llm(relevance_prompt)
        
        # Extract the response text
        if isinstance(llm_response, dict) and 'response' in llm_response:
            response_text = llm_response['response']
        else:
            response_text = str(llm_response)
        
        self.logger.info(f"LLM relevance response: {response_text}")
        
        # Parse JSON from the response
        import re
        import json
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                llm_result = json.loads(json_match.group(0))
                
                # Validate and format the response
                is_relevant = llm_result.get('is_eao_relevant', True)
                confidence = float(llm_result.get('confidence', 0.7))
                reasoning = llm_result.get('reasoning', ["LLM analysis completed"])
                recommendation = llm_result.get('recommendation', 'proceed_with_search')
                query_type = llm_result.get('query_type', 'unknown')
                suggested_response = llm_result.get('suggested_response', None)
                
                self.logger.info(f"LLM relevance analysis - Relevant: {is_relevant}, Confidence: {confidence}, Type: {query_type}")
                
                return {
                    "tool": "check_query_relevance",
                    "query": query,
                    "is_eao_relevant": is_relevant,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "recommendation": recommendation,
                    "query_type": query_type,
                    "suggested_response": suggested_response,
                    "method": "llm_analysis"
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Failed to parse LLM relevance JSON: {e}")
                self.logger.error(f"LLM response: {response_text}")
                raise Exception(f"LLM returned invalid JSON: {e}")
        else:
            self.logger.error(f"No JSON found in LLM relevance response: {response_text}")
            raise Exception("LLM did not return valid JSON format")

    async def _rule_based_relevance_check(self, query: str, context: str) -> Dict[str, Any]:
        """Enhanced rule-based fallback for query relevance checking."""
        
        # Define EAO-related keywords and terms
        eao_keywords = [
            # Core EAO terms
            "environmental assessment", "eao", "environmental assessment office",
            "environmental review", "environmental impact", "environmental study",
            "environmental screening", "environmental approval", "environmental certificate",
            
            # Project types commonly assessed by EAO
            "mining", "mine", "natural gas", "lng", "pipeline", "transmission line",
            "wind farm", "solar", "hydroelectric", "dam", "resort", "ski resort",
            "waste management", "landfill", "quarry", "gravel pit", "aggregate",
            "port", "terminal", "ferry", "infrastructure", "highway", "rail",
            
            # Environmental topics
            "wildlife", "habitat", "species", "endangered", "biodiversity",
            "air quality", "water quality", "soil", "contamination", "pollution",
            "greenhouse gas", "emissions", "carbon", "climate change",
            "fisheries", "salmon", "marine", "aquatic", "wetland", "forest",
            "first nations", "indigenous", "aboriginal", "consultation",
            "archaeology", "cultural heritage", "traditional use",
            
            # Assessment process terms
            "scoping", "baseline", "mitigation", "monitoring", "compliance",
            "public consultation", "stakeholder", "comment period",
            "certificate", "approval", "permit", "authorization",
            "proponent", "application", "proposal", "project description",
            
            # Government and regulatory
            "british columbia", "bc", "canada", "federal", "provincial",
            "ministry", "government", "regulation", "policy", "legislation",
            "ceaa", "impact assessment act", "environmental protection",
            
            # Geographic regions in BC
            "vancouver island", "lower mainland", "fraser valley", "peace river",
            "northern bc", "interior", "coastal", "yukon", "northwest territories"
        ]
        
        # Check for obvious non-EAO queries
        non_eao_indicators = [
            # Sports
            "soccer", "football", "hockey", "basketball", "baseball", "tennis",
            "olympics", "world cup", "championship", "league", "team", "player",
            "game", "match", "score", "season",
            
            # Entertainment
            "movie", "film", "actor", "actress", "director", "tv", "television",
            "music", "song", "album", "artist", "band", "concert", "celebrity",
            "netflix", "streaming", "show", "series",
            
            # Technology (unless environmental context)
            "iphone", "android", "windows", "mac", "computer", "software",
            "app", "website", "internet", "social media", "facebook", "twitter",
            "instagram", "youtube", "google", "microsoft", "apple",
            
            # Food and cooking
            "recipe", "cooking", "restaurant", "food", "meal", "ingredient",
            "diet", "nutrition", "calories", "chef", "kitchen",
            
            # Fashion and shopping
            "clothes", "fashion", "shopping", "store", "brand", "style",
            "shoes", "dress", "shirt", "pants", "jacket",
            
            # Finance (unless environmental finance)
            "stock", "investment", "bank", "credit", "loan", "mortgage",
            "crypto", "bitcoin", "trading", "market", "economy",
            
            # Travel (unless environmental tourism)
            "vacation", "hotel", "flight", "airline", "cruise", "tourism",
            "destination", "travel", "booking", "trip",
            
            # Personal/medical
            "health", "doctor", "medicine", "hospital", "symptoms", "disease",
            "therapy", "treatment", "prescription", "medical"
        ]
        
        # Convert query to lowercase for matching
        query_lower = query.lower()
        context_lower = context.lower() if context else ""
        full_text = f"{query_lower} {context_lower}".strip()
        
        # Count EAO-related matches
        eao_matches = []
        for keyword in eao_keywords:
            if keyword.lower() in full_text:
                eao_matches.append(keyword)
        
        # Count non-EAO indicators
        non_eao_matches = []
        for indicator in non_eao_indicators:
            if indicator.lower() in query_lower:  # Only check query, not context
                non_eao_matches.append(indicator)
        
        # Calculate relevance score
        eao_score = len(eao_matches) * 2  # EAO keywords get double weight
        non_eao_score = len(non_eao_matches) * 3  # Non-EAO indicators get triple penalty
        
        # Enhanced logic for RAG database searches
        # Be more permissive for searches that could be in EAO documents
        
        # Check for patterns that suggest RAG-appropriate searches
        rag_indicators = [
            # Document types commonly found in EAO processes
            "certificate", "correspondence", "report", "study", "assessment",
            "application", "submission", "filing", "document", "letter",
            "memo", "memorandum", "agreement", "contract", "permit",
            "approval", "authorization", "notice", "notification",
            "tax", "financial", "economic", "budget", "cost",
            
            # Process-related terms
            "consultation", "engagement", "meeting", "workshop", "hearing",
            "review", "comment", "response", "feedback", "input",
            "recommendation", "condition", "requirement", "compliance",
            
            # Geographic and proper noun patterns (common in EAO docs)
            "band", "nation", "first nations", "indigenous", "aboriginal",
            "creek", "river", "lake", "mountain", "valley", "island",
            "road", "highway", "bridge", "trail", "reserve",
            "ltd", "inc", "corp", "company", "limited", "corporation",
            
            # Industry terms that appear in EAO contexts
            "mine", "mining", "extraction", "drilling", "exploration",
            "development", "construction", "operation", "facility",
            "plant", "site", "location", "area", "zone", "region"
        ]
        
        # Check if query contains RAG-appropriate terms
        rag_matches = []
        for indicator in rag_indicators:
            if indicator.lower() in query_lower:
                rag_matches.append(indicator)
        
        # Special handling for short queries (likely proper nouns or specific terms)
        is_short_query = len(query.split()) <= 3
        has_capital_letters = any(c.isupper() for c in query)  # Likely proper nouns
        
        # Determine if query is EAO-relevant with enhanced logic
        is_relevant = False
        confidence = 0.0
        reasoning = []
        
        if non_eao_score > 0 and eao_score == 0 and len(rag_matches) == 0:
            # Clear non-EAO query with no environmental or RAG context
            is_relevant = False
            confidence = min(0.9, 0.5 + (non_eao_score * 0.1))
            reasoning.append(f"Non-EAO indicators detected: {', '.join(non_eao_matches[:3])}")
            reasoning.append("No environmental assessment or document-related keywords found")
        elif eao_score > 0:
            # Contains EAO keywords - definitely relevant
            is_relevant = True
            confidence = min(0.9, 0.6 + (eao_score * 0.05))
            reasoning.append(f"EAO-related keywords detected: {', '.join(eao_matches[:3])}")
        elif len(rag_matches) > 0:
            # Contains RAG/document-related terms - likely relevant
            is_relevant = True
            confidence = 0.7
            reasoning.append(f"Document/process terms detected: {', '.join(rag_matches[:3])}")
            reasoning.append("Query appears to be searching for documents or process-related content")
        elif is_short_query and has_capital_letters:
            # Short query with capital letters - likely proper nouns (project names, locations, companies)
            is_relevant = True
            confidence = 0.6
            reasoning.append("Short query with proper nouns detected")
            reasoning.append("Likely searching for specific projects, locations, or entities in EAO documents")
        elif is_short_query and len(query.strip()) > 0:
            # Any short, non-empty query could be relevant for RAG search
            is_relevant = True
            confidence = 0.5
            reasoning.append("Short query detected - allowing for RAG database search")
            reasoning.append("RAG databases can contain any relevant terms from EAO documents")
        else:
            # Check for generic environmental terms as fallback
            generic_env_terms = ["environment", "environmental", "ecology", "nature", "green", "sustainability"]
            generic_matches = [term for term in generic_env_terms if term in full_text]
            
            if generic_matches:
                is_relevant = True
                confidence = 0.4
                reasoning.append(f"Generic environmental terms: {', '.join(generic_matches)}")
                reasoning.append("Assuming environmental relevance - may be related to assessments")
            else:
                # Default to allowing for RAG search unless clearly non-EAO
                is_relevant = True
                confidence = 0.3
                reasoning.append("No clear EAO indicators, but allowing for RAG database search")
                reasoning.append("Query may reference content within EAO documents")
        
        # Build response
        result = {
            "tool": "check_query_relevance",
            "query": query,
            "is_eao_relevant": is_relevant,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "eao_keywords_found": eao_matches,
            "non_eao_indicators": non_eao_matches,
            "rag_keywords_found": rag_matches,
            "recommendation": "proceed_with_search" if is_relevant else "inform_user_out_of_scope",
            "suggested_response": None if is_relevant else 
                "I'm designed to help with Environmental Assessment Office (EAO) related queries about environmental assessments, projects, and regulatory processes in British Columbia. Your question appears to be outside this scope. Please ask about environmental assessments, projects under review, or EAO processes.",
            "method": "rule_based_fallback"
        }
        
        self.logger.info(f"Rule-based query relevance check complete - Relevant: {is_relevant}, Confidence: {confidence}")
        return result
