"""Agent-based query processing with tool execution capabilities."""

import json
import logging
from typing import Dict, Any, List, Optional
from flask import request
from ....clients.vector_search_client import VectorSearchClient

logger = logging.getLogger(__name__)


class VectorSearchAgent:
    """Agent that can execute complex queries using available VectorSearchClient tools."""
    
    def __init__(self, llm_client=None, user_location: Optional[Dict[str, Any]] = None):
        """Initialize the agent with available tools and optional LLM client.
        
        Args:
            llm_client: Optional LLM client for intelligent planning (otherwise uses rule-based)
            user_location: Optional user location data for location-aware queries
        """
        self.available_tools = self._get_available_tools()
        self.llm_client = llm_client
        self.user_location = user_location
    
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get the list of available tools from VectorSearchClient.
        
        Returns:
            List of tool definitions with names, descriptions, and parameters
        """
        tools = [
            {
                "name": "search",
                "description": "Perform vector similarity search with various strategies",
                "parameters": {
                    "query": "search query text (required)",
                    "project_ids": "list of project IDs to search in (optional list)",
                    "document_type_ids": "list of document type IDs to filter (optional list)",
                    "search_strategy": "search strategy to use (optional string)"
                },
                "returns": "search results with documents and similarity scores"
            },
            {
                "name": "get_document_similarity", 
                "description": "Find documents similar to a specific document",
                "parameters": {
                    "document_id": "ID of the reference document (required string)",
                    "project_ids": "list of project IDs to search in (optional list)"
                },
                "returns": "similar documents with similarity scores"
            },
            {
                "name": "get_projects_list",
                "description": "Get all available projects in the system",
                "parameters": {},
                "returns": "list of projects with IDs and names"
            },
            {
                "name": "get_document_types", 
                "description": "Get all available document types",
                "parameters": {},
                "returns": "dictionary of document types with metadata"
            },
            {
                "name": "get_search_strategies",
                "description": "Get available search strategies and their capabilities", 
                "parameters": {},
                "returns": "dictionary of search strategies with descriptions"
            },
            {
                "name": "get_project_statistics",
                "description": "Get processing statistics and document counts for projects",
                "parameters": {
                    "project_ids": "optional list of specific project IDs"
                },
                "returns": "statistics about document processing and indexing"
            }
        ]
        return tools
    
    def create_execution_plan(self, query: str, reason: str) -> List[Dict[str, Any]]:
        """Create an execution plan for the given query.
        
        Args:
            query: The user query
            reason: Why it was classified as agent-required
            
        Returns:
            List of execution steps with tools and parameters
        """
        if self.llm_client:
            return self._create_llm_execution_plan(query, reason)
        else:
            return self._create_rule_based_execution_plan(query, reason)
    
    def _create_llm_execution_plan(self, query: str, reason: str) -> List[Dict[str, Any]]:
        """Create an execution plan using LLM reasoning.
        
        Args:
            query: The user query
            reason: Why it was classified as agent-required
            
        Returns:
            List of execution steps
        """
        tools_context = self._format_tools_for_llm()
        
        # Get user location context for location-aware planning
        user_location = self._get_user_location_context()
        location_context = ""
        if user_location:
            location_info = []
            if 'city' in user_location:
                location_info.append(f"City: {user_location['city']}")
            if 'region' in user_location:
                location_info.append(f"Region: {user_location['region']}")
            if 'latitude' in user_location and 'longitude' in user_location:
                location_info.append(f"Coordinates: {user_location['latitude']}, {user_location['longitude']}")
            
            location_context = f"\nUSER LOCATION: {'; '.join(location_info)}"
        else:
            location_context = "\nUSER LOCATION: Not provided (default to British Columbia context)"
        
        planning_prompt = f"""You are an intelligent agent that can execute queries using available tools.

USER QUERY: "{query}"
COMPLEXITY REASON: {reason}{location_context}

{tools_context}

TASK: Create a step-by-step execution plan to answer the user's query using the available tools.

GUIDELINES:
1. Always start by getting context (projects, document types) if needed
2. Use semantic search with appropriate keywords for temporal queries
3. Use multiple tool calls if needed for complex queries
4. Optimize for getting comprehensive results
5. For temporal analysis, embed date keywords directly in search queries
6. For location queries (containing "local", "near me", "nearby", etc.), use location-specific keywords:
   - If user location is provided, include the city/region names in the search query
   - Always include "British Columbia" and "BC" for EAO context
   - Add relevant geographic terms to improve semantic matching
7. NEVER use placeholder text - only concrete parameters
8. Remember: NO date filtering or geographic filtering exists - use semantic search with relevant keywords

EXAMPLES:
- For "before 2020": search(query="environmental assessment 2019 2018 2017 before 2020")
- For "recent projects": search(query="environmental assessment 2023 2024 2025 recent latest")
- For "local projects" with Vancouver location: search(query="environmental assessment local Vancouver British Columbia BC")
- For "near me" with no location: search(query="environmental assessment local British Columbia BC Victoria Vancouver")

Respond with a JSON array of execution steps:
[
  {{
    "step_name": "descriptive_step_name",
    "tool": "tool_name",
    "parameters": {{"param": "value"}},
    "reasoning": "why this step is needed"
  }}
]

JSON Response:"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert query planning agent. Respond with valid JSON only."},
                {"role": "user", "content": planning_prompt}
            ]
            
            response = self.llm_client._make_llm_call(messages, temperature=0.1, max_tokens=800)
            
            if response and "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"].strip()
                content_clean = content.replace("```json", "").replace("```", "").strip()
                
                execution_plan = json.loads(content_clean)
                logger.info(f"🤖 AGENT: LLM created execution plan with {len(execution_plan)} steps")
                return execution_plan
            else:
                logger.warning("🤖 AGENT: LLM planning failed, falling back to rule-based")
                return self._create_rule_based_execution_plan(query, reason)
                
        except Exception as e:
            logger.error(f"🤖 AGENT: Error in LLM planning: {e}, falling back to rule-based")
            return self._create_rule_based_execution_plan(query, reason)
    
    def _format_tools_for_llm(self) -> str:
        """Format tools list for LLM context with constraints."""
        tools_text = "AVAILABLE TOOLS AND CONSTRAINTS:\n\n"
        
        for i, tool in enumerate(self.available_tools, 1):
            tools_text += f"{i}. {tool['name']}\n"
            tools_text += f"   Description: {tool['description']}\n"
            tools_text += f"   Parameters: {tool['parameters']}\n"
            tools_text += f"   Returns: {tool['returns']}\n\n"
        
        tools_text += """
CRITICAL CONSTRAINTS:
- NO temporal/date filtering is available - documents cannot be filtered by date
- NO geographic/location filtering is available - documents cannot be filtered by location fields
- project_ids must be actual project ID lists (not placeholder strings)
- document_type_ids must be actual document type ID lists (not placeholder strings)
- search() parameters: query (required), project_ids (optional list), document_type_ids (optional list), search_strategy (optional string)
- For temporal queries, use semantic search with date-related keywords in the query text
- For location queries, use semantic search with location-related keywords in the query text
- Always use concrete values, never placeholder text like "list of project IDs"

TEMPORAL QUERY APPROACH (Keyword Stuffing):
- NO database-level date filtering exists - this uses semantic search with temporal keywords
- For temporal queries, embed date-related keywords directly in the query text
- This relies on documents containing explicit date mentions in their content
- Example: "environmental assessment 2019 2018 2017 before 2020" hopes to find docs mentioning those years
- Be transparent: this is keyword stuffing, not true date filtering
- Always suggest date filtering tools for proper temporal capabilities

LOCATION QUERY APPROACH (Keyword Stuffing):
- NO database-level location filtering exists - this uses semantic search with location keywords
        - NO user location detection available in API - relies on context and request body parameters
- For "near me" queries with no location context, default to British Columbia scope
- IF client provides location parameters (lat/lng or city), use those for location stuffing
- IF no location provided, use BC context: "Victoria Vancouver British Columbia BC EAO"
- Example: "projects near me" becomes "projects British Columbia BC Victoria Vancouver" (BC default)
- Example with location: "projects near me" + lat/lng → "projects Victoria Vancouver Island BC"
- This relies on documents containing explicit location mentions in their content
- Be transparent: this is keyword stuffing, not true geographic filtering
- Always suggest location filtering tools for proper geographic capabilities

TEMPORAL QUERY STRATEGY:
- For "before 2020" queries, use semantic search with keywords like "2019 2018 2017 before 2020"
- For "recent" queries, use semantic search with keywords like "2023 2024 2025 recent latest"
- Combine temporal keywords with the main query terms
- Acknowledge limitations and suggest proper date filtering tools when relevant

LOCATION QUERY STRATEGY:
- For "near me" queries, use semantic search with BC location keywords like "Victoria Vancouver Island British Columbia BC"
- For specific locations mentioned (e.g., "near Langford"), keep the original location terms
- For regional queries, add broader geographic terms like "British Columbia BC Lower Mainland Vancouver Island"
- Combine location keywords with the main query terms
- Acknowledge limitations and suggest proper geographic filtering tools when relevant
"""
        return tools_text
    
    def _get_user_location_context(self) -> Optional[Dict[str, Any]]:
        """Get user location from stored user_location attribute.
        
        This method now uses the user_location passed from the request body
        instead of extracting from headers to avoid CORS issues.
        
        Returns:
            Dict with location context or None if not available
        """
        if self.user_location:
            logger.info(f"🌍 LOCATION: Using location from request body: {self.user_location}")
            return self.user_location
        
        logger.debug("🌍 LOCATION: No user location available")
        return None

    def _enhance_query_with_location_keywords(self, query: str) -> str:
        """Enhance query with location keywords if it contains location-related terms.
        
        Args:
            query: Original search query
            
        Returns:
            Enhanced query with location keywords, or original query if no enhancement needed
        """
        query_lower = query.lower()
        
        # Check if query contains location-related terms
        location_terms = ["local", "near me", "nearby", "close to", "in my area", "regional", "area"]
        has_location_terms = any(term in query_lower for term in location_terms)
        
        if not has_location_terms:
            return query
            
        # Get user location for keyword stuffing
        user_location = self._get_user_location_context()
        location_keywords = []
        
        if user_location:
            # Use provided location for keyword stuffing
            if 'city' in user_location:
                location_keywords.append(user_location['city'])
            if 'region' in user_location:
                location_keywords.append(user_location['region'])
                
            logger.info(f"🌍 LOCATION STUFFING: Using user location: {user_location}")
        
        # Always add BC context since this is EAO (British Columbia Environmental Assessment Office)
        if not any(bc_term in ' '.join(location_keywords).lower() for bc_term in ['bc', 'british columbia']):
            location_keywords.extend(['British Columbia', 'BC'])
        
        if location_keywords:
            enhanced_query = f"{query} {' '.join(location_keywords)}"
            logger.info(f"🌍 LOCATION STUFFING: Enhanced query with keywords: {location_keywords}")
            return enhanced_query
        
        return query

    def _enhance_query_with_temporal_keywords(self, query: str) -> str:
        """Enhance query with temporal keywords if it contains time-related terms.
        
        Args:
            query: Original search query
            
        Returns:
            Enhanced query with temporal keywords, or original query if no enhancement needed
        """
        query_lower = query.lower()
        
        # Check if query contains temporal terms
        temporal_terms = ["before", "after", "recent", "latest", "current", "new", "last", "time", "date", "year"]
        has_temporal_terms = any(term in query_lower for term in temporal_terms)
        
        if not has_temporal_terms:
            return query
            
        temporal_keywords = []
        
        # Add temporal keywords based on query context
        if any(word in query_lower for word in ["before", "prior", "earlier"]):
            temporal_keywords.extend(["2019", "2018", "2017", "before", "2020"])
            logger.info("⏰ TEMPORAL STUFFING: Adding historical date keywords")
        elif any(word in query_lower for word in ["recent", "latest", "current", "new", "last"]):
            temporal_keywords.extend(["2023", "2024", "2025", "recent", "latest"])
            logger.info("⏰ TEMPORAL STUFFING: Adding recent date keywords")
        
        if temporal_keywords:
            enhanced_query = f"{query} {' '.join(temporal_keywords)}"
            logger.info(f"⏰ TEMPORAL STUFFING: Enhanced query with keywords: {temporal_keywords}")
            return enhanced_query
        
        return query

    def _enhance_query_with_keywords(self, query: str) -> str:
        """Enhance query with both location and temporal keywords if applicable.
        
        Args:
            query: Original search query
            
        Returns:
            Enhanced query with relevant keywords
        """
        # Apply temporal enhancement first
        enhanced_query = self._enhance_query_with_temporal_keywords(query)
        
        # Then apply location enhancement
        enhanced_query = self._enhance_query_with_location_keywords(enhanced_query)
        
        return enhanced_query
    
    def _create_rule_based_execution_plan(self, query: str, reason: str) -> List[Dict[str, Any]]:
        """Create an execution plan using rule-based logic.
        
        Args:
            query: The user query
            reason: Why it was classified as agent-required  
            
        Returns:
            List of execution steps with tools and parameters
        """
        
        plan = []
        query_lower = query.lower()
        
        # Always start by getting available context
        plan.append({
            "step_name": "get_available_projects",
            "tool": "get_projects_list",
            "parameters": {},
            "reasoning": "Get available projects for context"
        })
        
        plan.append({
            "step_name": "get_available_document_types", 
            "tool": "get_document_types",
            "parameters": {},
            "reasoning": "Get available document types for context"
        })
        
        # Rule-based logic for different query types
        if any(word in query_lower for word in ["compare", "comparison", "versus", "vs"]):
            plan.append({
                "step_name": "get_search_strategies",
                "tool": "get_search_strategies", 
                "parameters": {},
                "reasoning": "Get search strategies for comparison queries"
            })
            
            # For comparison queries, we might need to do multiple searches
            plan.append({
                "step_name": "exploratory_search",
                "tool": "search",
                "parameters": {
                    "query": query
                },
                "reasoning": "Perform exploratory search for comparison analysis"
            })
        
        elif any(word in query_lower for word in ["statistics", "stats", "count", "how many"]):
            plan.append({
                "step_name": "get_project_statistics",
                "tool": "get_project_statistics",
                "parameters": {},
                "reasoning": "Get project statistics for statistical queries"
            })
        
        elif any(word in query_lower for word in ["time", "date", "recent", "last", "before", "after"]):
            # For temporal queries, use semantic search with temporal keywords (keyword stuffing approach)
            if any(word in query_lower for word in ["before", "prior", "earlier"]):
                temporal_query = f"{query} 2019 2018 2017 before 2020"
                reasoning = "Use semantic search with date keywords (keyword stuffing) - suggests documents mentioning these years. NOTE: No true date filtering available, consider adding date filtering tools."
            elif any(word in query_lower for word in ["recent", "latest", "current", "new"]):
                temporal_query = f"{query} 2023 2024 2025 recent latest"
                reasoning = "Use semantic search with recent date keywords (keyword stuffing) - suggests documents mentioning recent years. NOTE: No true date filtering available, consider adding date filtering tools."
            else:
                temporal_query = query
                reasoning = "Temporal query detected but no specific time period identified - using original query"
            
            plan.append({
                "step_name": "temporal_keyword_search",
                "tool": "search",
                "parameters": {
                    "query": temporal_query
                },
                "reasoning": reasoning
            })

        elif any(phrase in query_lower for phrase in ["near me", "nearby", "close to me", "in my area", "local"]):
            # For location queries, use semantic search with location keywords (keyword stuffing approach)
            user_location = self._get_user_location_context()
            
            if user_location:
                # Use provided location for keyword stuffing
                location_keywords = []
                
                if 'city' in user_location:
                    location_keywords.append(user_location['city'])
                if 'region' in user_location:
                    location_keywords.append(user_location['region'])
                    
                # Add BC context if not already present
                if not any(bc_term in ' '.join(location_keywords).lower() for bc_term in ['bc', 'british columbia']):
                    location_keywords.extend(['British Columbia', 'BC'])
                
                location_query = f"{query} {' '.join(location_keywords)}"
                reasoning = f"Use semantic search with user location keywords (keyword stuffing) - using location from request body: {user_location}. NOTE: No true geographic filtering available, consider adding location filtering tools."
            else:
                # Default to BC context since this is EAO (British Columbia Environmental Assessment Office)
                location_query = f"{query} British Columbia BC Victoria Vancouver"
                reasoning = "Use semantic search with BC location keywords (keyword stuffing) - defaults to BC context since no user location available in request body. NOTE: No true geographic filtering available, consider adding location filtering tools."
            
            plan.append({
                "step_name": "location_keyword_search", 
                "tool": "search",
                "parameters": {
                    "query": location_query
                },
                "reasoning": reasoning
            })
        
        else:
            # Default: comprehensive search
            plan.append({
                "step_name": "comprehensive_search",
                "tool": "search",
                "parameters": {
                    "query": query
                },
                "reasoning": "Perform comprehensive search for complex query"
            })
        
        return plan
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given parameters.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            
        Returns:
            Result of the tool execution
        """
        try:
            # Validate parameters before execution
            validation_error = self._validate_parameters(tool_name, parameters)
            if validation_error:
                logger.error(f"🤖 AGENT: Parameter validation failed for '{tool_name}': {validation_error}")
                return {"success": False, "error": f"Parameter validation failed: {validation_error}"}
            
            logger.info(f"🤖 AGENT: Executing tool '{tool_name}' with parameters: {parameters}")
            
            if tool_name == "search":
                # Apply both location and temporal keyword stuffing for relevant queries
                original_query = parameters.get("query", "")
                enhanced_query = self._enhance_query_with_keywords(original_query)
                
                result = VectorSearchClient.search(
                    query=enhanced_query,
                    project_ids=parameters.get("project_ids", []),
                    document_type_ids=parameters.get("document_type_ids", []),
                    search_strategy=parameters.get("search_strategy", "")
                )
                
                # Log if query was enhanced
                if enhanced_query != original_query:
                    logger.info(f"🔍 QUERY STUFFING: Enhanced query from '{original_query}' to '{enhanced_query}'")
            elif tool_name == "get_document_similarity":
                result = VectorSearchClient.get_document_similarity(
                    document_id=parameters.get("document_id", ""),
                    project_ids=parameters.get("project_ids", [])
                )
            elif tool_name == "get_projects_list":
                result = VectorSearchClient.get_projects_list()
            elif tool_name == "get_document_types":
                result = VectorSearchClient.get_document_types()
            elif tool_name == "get_search_strategies":
                result = VectorSearchClient.get_search_strategies()
            elif tool_name == "get_project_statistics":
                result = VectorSearchClient.get_project_statistics(
                    project_ids=parameters.get("project_ids")
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            logger.info(f"🤖 AGENT: Tool '{tool_name}' executed successfully")
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"🤖 AGENT: Error executing tool '{tool_name}': {e}")
            return {"success": False, "error": str(e)}

    def _generate_temporal_tool_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Generate tool suggestions for proper temporal filtering.
        
        Args:
            query: The temporal query that prompted this
            
        Returns:
            List of suggested tools for temporal functionality
        """
        suggestions = []
        
        if any(word in query.lower() for word in ["before", "after", "date", "time", "recent", "last"]):
            suggestions.append({
                "function_name": "search_by_date_range",
                "description": "Filter documents by date fields (created_date, published_date, assessment_date)",
                "endpoint": "/api/search/date-range",
                "justification": "Enable true temporal filtering instead of keyword stuffing",
                "priority": "HIGH",
                "parameters": {
                    "query": "search query text",
                    "date_from": "start date (YYYY-MM-DD)",
                    "date_to": "end date (YYYY-MM-DD)", 
                    "date_field": "field to filter on (created_date|published_date|assessment_date)"
                }
            })
            
            suggestions.append({
                "function_name": "get_documents_by_time_period",
                "description": "Retrieve documents from specific time periods with temporal sorting",
                "endpoint": "/api/documents/time-period",
                "justification": "Provide chronological document access with proper date indexing",
                "priority": "HIGH",
                "parameters": {
                    "time_period": "relative time (last_year|last_5_years|before_2020|after_2020)",
                    "sort_by": "temporal sorting (newest_first|oldest_first|relevance)",
                    "limit": "maximum results"
                }
            })
            
            suggestions.append({
                "function_name": "get_temporal_document_metadata",
                "description": "Extract and index temporal metadata from documents",
                "endpoint": "/api/documents/temporal-metadata",
                "justification": "Enable discovery of date fields within document content for better temporal search",
                "priority": "MEDIUM",
                "parameters": {
                    "extract_dates": "boolean to extract dates from content",
                    "date_patterns": "list of date patterns to recognize"
                }
            })
        
        return suggestions

    def _generate_location_tool_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Generate tool suggestions for proper location filtering.
        
        Args:
            query: The location query that prompted this
            
        Returns:
            List of suggested tools for location functionality
        """
        suggestions = []
        
        if any(phrase in query.lower() for phrase in ["near me", "nearby", "close to", "local", "location", "area"]):
            # Check if location data is available from request body
            user_location = self._get_user_location_context()
            location_context = " (Note: Currently using location from request body)" if user_location else ""
            
            suggestions.append({
                "function_name": "search_by_location",
                "description": "Filter documents by geographic location with radius search",
                "endpoint": "/api/search/location",
                "justification": f"Enable true geographic filtering instead of keyword stuffing{location_context}",
                "priority": "HIGH",
                "parameters": {
                    "query": "search query text",
                    "lat": "latitude coordinate",
                    "lng": "longitude coordinate",
                    "radius_km": "search radius in kilometers",
                    "location_field": "field to filter on (project_location|site_coordinates)"
                }
            })
            
            suggestions.append({
                "function_name": "get_user_location_context",
                "description": "Detect user location from request body, IP, or client-provided coordinates",
                "endpoint": "/api/user/location",
                "justification": f"Enable automatic location detection for 'near me' queries{location_context}",
                "priority": "HIGH" if not user_location else "MEDIUM",
                "current_status": "Location data available" if user_location else "No location data provided",
                "parameters": {
                    "use_ip_geolocation": "boolean to enable IP-based location detection",
                    "client_lat": "optional client-provided latitude", 
                    "client_lng": "optional client-provided longitude",
                    "header_examples": "X-User-Location, X-User-City, X-User-Latitude/X-User-Longitude"
                }
            })
            
            suggestions.append({
                "function_name": "get_projects_by_region",
                "description": "Retrieve projects grouped by administrative regions (municipalities, regional districts)",
                "endpoint": "/api/projects/by-region",
                "justification": "Provide regional project access with proper geographic indexing",
                "priority": "MEDIUM",
                "parameters": {
                    "region_type": "region type (municipality|regional_district|electoral_area)",
                    "region_name": "specific region name",
                    "include_adjacent": "boolean to include adjacent regions"
                }
            })
        
        return suggestions

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate parameters for a tool before execution.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        if tool_name == "search":
            # Check for placeholder strings in list parameters
            project_ids = parameters.get("project_ids", [])
            if isinstance(project_ids, str):
                return f"project_ids must be a list, not string: '{project_ids}'"
            
            document_type_ids = parameters.get("document_type_ids", [])
            if isinstance(document_type_ids, str):
                return f"document_type_ids must be a list, not string: '{document_type_ids}'"
                
        elif tool_name == "get_document_similarity":
            document_id = parameters.get("document_id", "")
            if not document_id or "ID of" in str(document_id):
                return f"document_id must be a concrete ID, not placeholder: '{document_id}'"
                
        return None  # Validation passed


def handle_agent_query(query: str, reason: str, llm_client=None, user_location: Optional[Dict[str, Any]] = None) -> dict:
    """Handle agent-required queries with tool execution.
    
    Args:
        query: The complex query that requires agent processing
        reason: Why the query was classified as agent-required
        llm_client: Optional LLM client for intelligent planning
        user_location: Optional user location data from request body
        
    Returns:
        Dict with agent processing results and any tool executions
    """
    
    logger.info("=" * 60)
    logger.info("🤖 AGENT MODE ACTIVATED")
    logger.info(f"Query: {query}")
    logger.info(f"Reason: {reason}")
    logger.info(f"LLM Planning: {'Enabled' if llm_client else 'Rule-based fallback'}")
    logger.info("=" * 60)
    
    try:
        # Initialize agent with user location
        agent = VectorSearchAgent(llm_client=llm_client, user_location=user_location)
        
        # Create execution plan (LLM-driven or rule-based)
        execution_plan = agent.create_execution_plan(query, reason)
        
        logger.info(f"🤖 AGENT: Execution plan created with {len(execution_plan)} steps")
        
        # Execute the plan
        results = []
        for step in execution_plan:
            tool_result = agent.execute_tool(step["tool"], step["parameters"])
            results.append({
                "step": step["step_name"],
                "tool": step["tool"],
                "parameters": step["parameters"],
                "reasoning": step.get("reasoning", ""),
                "result": tool_result
            })
        
        logger.info(f"🤖 AGENT: Completed {len(results)} tool executions")
        
        # Analyze results for summary
        successful_executions = [r for r in results if r["result"].get("success", False)]
        failed_executions = [r for r in results if not r["result"].get("success", False)]
        
        logger.info(f"🤖 AGENT: {len(successful_executions)} successful, {len(failed_executions)} failed executions")
        
        # Generate tool suggestions for temporal and location queries
        temporal_suggestions = []
        location_suggestions = []
        
        if any(word in query.lower() for word in ["before", "after", "date", "time", "recent", "last"]):
            temporal_suggestions = agent._generate_temporal_tool_suggestions(query)
            logger.info(f"🤖 AGENT: Generated {len(temporal_suggestions)} temporal tool suggestions")
            
        if any(phrase in query.lower() for phrase in ["near me", "nearby", "close to", "local", "location", "area"]):
            location_suggestions = agent._generate_location_tool_suggestions(query)
            logger.info(f"🤖 AGENT: Generated {len(location_suggestions)} location tool suggestions")
        
        # Determine approaches used
        approach_info = {}
        if temporal_suggestions:
            approach_info["temporal_approach"] = "keyword_stuffing"
        if location_suggestions:
            approach_info["location_approach"] = "keyword_stuffing_bc_default"
        
        logger.info("=" * 60)
        
        return {
            "agent_attempted": True,
            "agent_implemented": True,
            "query": query,
            "reason": reason,
            "planning_method": "LLM-driven" if llm_client else "Rule-based",
            "execution_plan": execution_plan,
            "tool_executions": results,
            "agent_success": len(failed_executions) == 0,
            **approach_info,
            "temporal_tool_suggestions": temporal_suggestions,
            "location_tool_suggestions": location_suggestions,
            "execution_summary": {
                "total_steps": len(results),
                "successful_steps": len(successful_executions),
                "failed_steps": len(failed_executions)
            }
        }
        
    except Exception as e:
        logger.error(f"🤖 AGENT: Error in agent processing: {e}")
        logger.info("=" * 60)
        
        return {
            "agent_attempted": True,
            "agent_implemented": True,
            "query": query,
            "reason": reason,
            "error": str(e),
            "fallback_to_normal_flow": True
        }


# Backward compatibility with existing interface
def _create_execution_plan(query: str, reason: str, available_tools: List[Dict]) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility."""
    agent = VectorSearchAgent()
    return agent._create_rule_based_execution_plan(query, reason)