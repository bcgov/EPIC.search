"""Agent-based query processing with tool execution capabilities."""

import json
import logging
from typing import Dict, Any, List, Optional
from flask import request
from ....clients.vector_search_client import VectorSearchClient

logger = logging.getLogger(__name__)


class VectorSearchAgent:
    """Agent that can execute complex queries using available VectorSearchClient tools."""
    
    def __init__(self, llm_client=None, user_location: Optional[Dict[str, Any]] = None, 
                 project_ids: Optional[List[str]] = None, document_type_ids: Optional[List[str]] = None,
                 search_strategy: Optional[str] = None, ranking: Optional[Dict[str, Any]] = None):
        """Initialize the agent with available tools and optional LLM client.
        
        Args:
            llm_client: Required LLM client for intelligent planning
            user_location: Optional user location data for location-aware queries
            project_ids: Optional user-provided project IDs to use in search calls
            document_type_ids: Optional user-provided document type IDs to use in search calls
            search_strategy: Optional user-provided search strategy to use in search calls
            ranking: Optional user-provided ranking configuration to use in search calls
        """
        self.available_tools = self._get_available_tools()
        self.llm_client = llm_client
        self.user_location = user_location
        self.user_project_ids = project_ids
        self.user_document_type_ids = document_type_ids
        self.user_search_strategy = search_strategy
        self.user_ranking = ranking
    
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
                    "project_ids": "list of project IDs to search in - use ALL matching IDs when multiple projects are relevant (optional list)",
                    "document_type_ids": "list of document type IDs to filter - use ALL matching IDs when multiple document types are relevant (optional list)",
                    "search_strategy": "search strategy to use (optional string)",
                    "ranking": "ranking configuration with minScore and topN (optional dict)"
                },
                "returns": "search results with documents and similarity scores"
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
            }
        ]
        return tools
    
    def create_execution_plan(self, query: str, reason: str) -> List[Dict[str, Any]]:
        """Create an intelligent execution plan using LLM reasoning.
        
        Args:
            query: The user query
            reason: Why it was classified as agent-required
            
        Returns:
            List of execution steps with tools and parameters
        """
        return self._create_llm_execution_plan(query, reason)
    
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
        
        planning_prompt = f"""You are an intelligent agent that follows a structured, user-guided approach to query execution.

USER QUERY: "{query}"
COMPLEXITY REASON: {reason}{location_context}

{tools_context}

MANDATORY 6-STEP APPROACH:
Follow these steps in order. Each step must be completed before proceeding to the next.

STEP 1: PROVIDE AVAILABLE TOOLS
- List all available tools and their purposes
- Explain what each tool can discover or search

STEP 2: CHECK USER-SUPPLIED CONTEXT
- Examine the user query for any explicitly mentioned project names, IDs, or document types
- If user provided specific project names or IDs, note them for direct use
- If user provided specific document types (letters, reports, assessments), note them
- Determine if context gathering steps can be skipped

STEP 3: GATHER MISSING CONTEXT (if needed)
- ONLY call get_projects_list() if Step 2 revealed no user-supplied project information
- ONLY call get_document_types() if Step 2 revealed no user-supplied document type information or query mentions specific document types
- Skip context tools if user already provided the needed IDs/names

STEP 4: ANALYZE AND CROSS-REFERENCE
- Cross-reference user query terms with discovered project names and document types
- Identify the most relevant project IDs and document type IDs for the search
- Plan semantic search keywords based on temporal, location, or topical requirements

STEP 5: EXECUTE UP TO 3 TARGETED SEARCHES
- Plan 1-3 search executions with the best available parameters
- Always use discovered project_ids and document_type_ids when available
- For temporal queries: embed date keywords in search query text
- For location queries: include geographic terms (city names, "British Columbia", "BC")
- For topic queries: use relevant domain-specific keywords

WHEN TO USE MULTIPLE SEARCHES:
- Multiple distinct projects mentioned: Create separate searches for each project to ensure comprehensive coverage
- Multiple document types with different contexts (e.g., technical reports vs. letters): Search separately for better precision
- Complex multi-faceted queries: Break into focused searches (e.g., one for technical aspects, one for public consultation)
- Temporal ranges: Separate searches for different time periods if they require different keyword strategies
- Different search strategies needed: Use different approaches (semantic vs keyword) for different aspects of the query

STEP 6: CONSOLIDATE AND SUGGEST
- Combine results from all searches
- Suggest additional tools or refinements if initial results are insufficient

CRITICAL RULES:
- NEVER call context tools if user already provided the needed information
- ALWAYS use both project_ids and document_type_ids in searches when available
- ALWAYS include ALL relevant matches - use multiple IDs when multiple projects/document types are detected
- NO placeholder text - only concrete, discovered parameters
- BALANCE EFFICIENCY vs PRECISION: Use multiple targeted searches when query complexity warrants it, single search when simple

EXAMPLES:
- User says "letters about South Anderson project": 
  → Call get_projects_list (need to find project ID for "South Anderson")
  → Call get_document_types (need to find document type ID for "letters")
  → Search with discovered project_id and document_type_id
- User says "recent environmental assessments":
  → Call get_projects_list (no specific project mentioned, get all projects)
  → Call get_document_types (need to find document type ID for "assessments")  
  → Search with assessment document_type_ids and "2023 2024 recent" keywords
- User says "letters and reports from Site C project":
  → Call get_projects_list (need to find project ID for "Site C") 
  → Call get_document_types (need to find document type IDs for "letters" AND "reports")
  → Search with discovered project_id and MULTIPLE document_type_ids: ["letters_id", "reports_id"]
- User says "documents from Site C and Trans Mountain projects":
  → Call get_projects_list (need to find project IDs for "Site C" AND "Trans Mountain")
  → Call get_document_types (need to find all relevant document types)
  → Search with MULTIPLE project_ids: ["sitec_id", "transmountain_id"] and relevant document_type_ids
- User says "technical reports about environmental impacts AND public letters about the same projects":
  → Get project and document type info
  → Search 1: Technical reports with "environmental impacts" query
  → Search 2: Letters with "public concerns opposition" query  
  → (Two searches for different document contexts and search focus)

CRITICAL: When multiple projects or document types are mentioned or relevant, ALWAYS include ALL matching IDs in the lists.
- project_ids: ["id1", "id2", "id3"] for multiple projects
- document_type_ids: ["id1", "id2"] for multiple document types
Don't limit to just one ID when multiple matches are found - use ALL relevant matches.

RESPONSE FORMAT:
Return ONLY valid JSON - no comments, no placeholder text, no markdown formatting.
ONLY create steps for the available tools listed above - no other tools exist.
DO NOT create analysis or reasoning steps - only executable tool calls.
For parameters, use empty objects {{}} if no parameters needed.
NEVER use comments like /* comment */ or placeholder text in JSON.

VALID JSON EXAMPLES:

Single project/document type:
[
  {{
    "step_name": "get_document_types",
    "tool": "get_document_types", 
    "parameters": {{}},
    "reasoning": "Need to find document type IDs for letters"
  }},
  {{
    "step_name": "search_for_letters",
    "tool": "search",
    "parameters": {{
      "query": "Nooaitch Indian Band letters South Anderson",
      "document_type_ids": ["letters_id_from_previous_step"],
      "search_strategy": "semantic"
    }},
    "reasoning": "Search for letters mentioning Nooaitch Indian Band"
  }}
]

Multiple projects/document types:
[
  {{
    "step_name": "get_projects_list",
    "tool": "get_projects_list",
    "parameters": {{}},
    "reasoning": "Need to find project IDs for Site C and Trans Mountain"
  }},
  {{
    "step_name": "get_document_types", 
    "tool": "get_document_types",
    "parameters": {{}},
    "reasoning": "Need to find document type IDs for letters and reports"
  }},
  {{
    "step_name": "search_multiple_projects_types",
    "tool": "search",
    "parameters": {{
      "query": "environmental impact Site C Trans Mountain letters reports",
      "project_ids": ["sitec_project_id", "transmountain_project_id"],
      "document_type_ids": ["letters_doc_type_id", "reports_doc_type_id"],
      "search_strategy": "semantic"
    }},
    "reasoning": "Search multiple projects and document types"
  }}
]"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert query planning agent. CRITICAL: Return ONLY valid JSON array. NO comments like /* */, NO placeholder text, NO markdown, NO explanations. Only use the available tools provided in the prompt. NO analysis steps. Raw JSON only."},
                {"role": "user", "content": planning_prompt}
            ]
            
            response = self.llm_client.chat_completion(messages, temperature=0.1, max_tokens=800)
            
            if response and "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"].strip()
                logger.info(f"🤖 AGENT: Raw LLM response content: {content[:500]}...")
                
                # Clean the content - remove markdown blocks and extra whitespace
                content_clean = self._clean_json_response(content)
                
                # Apply common JSON fixes
                content_clean = self._fix_common_json_issues(content_clean)
                
                logger.info(f"🤖 AGENT: Cleaned content for JSON parsing: {content_clean[:200]}...")
                
                try:
                    execution_plan = json.loads(content_clean)
                    if isinstance(execution_plan, list) and len(execution_plan) > 0:
                        # Validate that each step has required fields
                        for i, step in enumerate(execution_plan):
                            required_fields = ["step_name", "tool", "parameters", "reasoning"]
                            missing_fields = [field for field in required_fields if field not in step]
                            if missing_fields:
                                logger.warning(f"🤖 AGENT: Step {i+1} missing required fields: {missing_fields}")
                        
                        logger.info(f"🤖 AGENT: LLM created execution plan with {len(execution_plan)} steps")
                        return execution_plan
                    else:
                        logger.error("🤖 AGENT: LLM planning failed - execution plan is not a valid list")
                        return []
                except json.JSONDecodeError as json_err:
                    logger.error(f"🤖 AGENT: JSON parsing failed: {json_err}")
                    logger.error(f"🤖 AGENT: Failed to parse content: {content_clean}")
                    logger.error(f"🤖 AGENT: JSON error details - Line: {json_err.lineno}, Column: {json_err.colno}")
                    return []
            else:
                logger.error("🤖 AGENT: LLM planning failed - no valid execution plan generated")
                return []
                
        except Exception as e:
            logger.error(f"🤖 AGENT: Error in LLM planning: {e}")
            logger.error(f"🤖 AGENT: Exception type: {type(e)}")
            logger.error(f"🤖 AGENT: Exception traceback:", exc_info=True)
            return []
    
    def _clean_json_response(self, content: str) -> str:
        """Clean LLM response content to extract valid JSON.
        
        Args:
            content: Raw LLM response content
            
        Returns:
            Cleaned JSON string
        """
        # Remove common markdown code block markers
        content = content.replace("```json", "").replace("```", "").strip()
        
        # Remove any leading/trailing markdown blocks
        while content.startswith('```'):
            newline_pos = content.find('\n')
            if newline_pos != -1:
                content = content[newline_pos + 1:].strip()
            else:
                content = content[3:].strip()
                
        while content.endswith('```'):
            content = content[:-3].strip()
        
        # Remove any explanatory text before JSON
        lines = content.split('\n')
        json_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('[') or line.strip().startswith('{'):
                json_start = i
                break
        
        if json_start >= 0:
            content = '\n'.join(lines[json_start:])
        
        # Remove any explanatory text after JSON
        # Find the last ] or } that might end the JSON
        last_bracket = max(content.rfind(']'), content.rfind('}'))
        if last_bracket != -1:
            content = content[:last_bracket + 1]
        
        return content.strip()
    
    def _fix_common_json_issues(self, content: str) -> str:
        """Fix common JSON syntax issues that LLMs often create.
        
        Args:
            content: JSON content to fix
            
        Returns:
            Fixed JSON content
        """
        import re
        
        # Fix missing commas between objects - look for } followed by " on next line
        # Pattern: }\n    "key" should become },\n    "key"
        content = re.sub(r'(\})\s*\n(\s*")', r'\1,\n\2', content)
        
        # Fix missing commas between array elements - look for } followed by { on next line  
        # Pattern: }\n  { should become },\n  {
        content = re.sub(r'(\})\s*\n(\s*\{)', r'\1,\n\2', content)
        
        # Fix missing commas within objects - look for " followed by " on next line
        # Pattern: "value"\n    "key" should become "value",\n    "key"
        content = re.sub(r'(")\s*\n(\s*")', r'\1,\n\2', content)
        
        # Fix missing commas after } within objects - look for } followed by " on next line (within object)
        # This is more specific than the first rule
        content = re.sub(r'(\})\s*\n(\s*"[^"]+"\s*:)', r'\1,\n\2', content)
        
        # Remove trailing commas before closing brackets/braces
        content = re.sub(r',(\s*[\]\}])', r'\1', content)
        
        return content
    

    
    def _should_skip_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Determine if a step should be skipped based on available context.
        
        Args:
            step: The execution step to evaluate
            context: Current execution context with discovered information
            
        Returns:
            True if step should be skipped, False otherwise
        """
        tool_name = step.get("tool", "")
        step_name = step.get("step_name", "").lower()
        parameters = step.get("parameters", {})
        query = parameters.get("query", "").lower()
        
        # Skip search steps that are looking for project IDs when we already have them
        if tool_name == "search" and context["discovered_project_ids"]:
            # Check if this search is looking for project identification
            if any(term in step_name for term in ["project id", "identify project", "find project"]):
                logger.info(f"🤖 SKIP: Already have project IDs: {context['discovered_project_ids']}")
                return True
            
            # Check if query is trying to find project info we already have
            if any(term in query for term in ["project id", "project name", "identify project"]):
                # But only skip if we're looking for a specific project we already found
                for project_name, project_id in context["project_name_to_id_mapping"].items():
                    if project_name in query:
                        logger.info(f"🤖 SKIP: Already have project_id for '{project_name}': {project_id}")
                        return True
        
        # Skip document type searches when we already have the mappings
        if tool_name == "search" and context["discovered_document_type_ids"]:
            if any(term in step_name for term in ["document type", "find document", "identify document"]):
                logger.info(f"🤖 SKIP: Already have document types: {context['discovered_document_type_ids']}")
                return True
        
        # Skip get_projects_list if we already executed it and have results  
        if tool_name == "get_projects_list" and context["project_name_to_id_mapping"]:
            logger.info("🤖 SKIP: Already have project list")
            return True
            
        # Skip get_document_types if we already executed it and have results
        if tool_name == "get_document_types" and context["document_type_name_to_id_mapping"]:
            logger.info("🤖 SKIP: Already have document types list")
            return True
        
        return False
    
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
- project_ids must be actual project ID lists (not placeholder strings) - include ALL matching project IDs
- document_type_ids must be actual document type ID lists (not placeholder strings) - include ALL matching document type IDs
- search() parameters: query (required), project_ids (optional list), document_type_ids (optional list), search_strategy (optional string)
- When multiple projects or document types are detected, use ALL relevant IDs in the respective lists
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
                
                # Prioritize user-provided parameters over LLM-generated ones
                final_project_ids = self.user_project_ids if self.user_project_ids is not None else parameters.get("project_ids", [])
                final_document_type_ids = self.user_document_type_ids if self.user_document_type_ids is not None else parameters.get("document_type_ids", [])
                final_search_strategy = self.user_search_strategy if self.user_search_strategy is not None else parameters.get("search_strategy", "")
                final_ranking = self.user_ranking if self.user_ranking is not None else parameters.get("ranking", None)
                
                # Log parameter usage
                if self.user_project_ids is not None:
                    logger.info(f"🤖 AGENT: Using user-provided project_ids: {final_project_ids}")
                elif parameters.get("project_ids"):
                    logger.info(f"🤖 AGENT: Using LLM-generated project_ids: {final_project_ids}")
                    
                if self.user_document_type_ids is not None:
                    logger.info(f"🤖 AGENT: Using user-provided document_type_ids: {final_document_type_ids}")
                elif parameters.get("document_type_ids"):
                    logger.info(f"🤖 AGENT: Using LLM-generated document_type_ids: {final_document_type_ids}")
                    
                if self.user_search_strategy is not None:
                    logger.info(f"🤖 AGENT: Using user-provided search_strategy: {final_search_strategy}")
                elif parameters.get("search_strategy"):
                    logger.info(f"🤖 AGENT: Using LLM-generated search_strategy: {final_search_strategy}")
                
                if self.user_ranking is not None:
                    logger.info(f"🤖 AGENT: Using user-provided ranking: {final_ranking}")
                elif parameters.get("ranking"):
                    logger.info(f"🤖 AGENT: Using LLM-generated ranking: {final_ranking}")
                
                result = VectorSearchClient.search(
                    query=enhanced_query,
                    project_ids=final_project_ids,
                    document_type_ids=final_document_type_ids,
                    search_strategy=final_search_strategy,
                    ranking=final_ranking
                )
                
                # Log if query was enhanced
                if enhanced_query != original_query:
                    logger.info(f"🔍 QUERY STUFFING: Enhanced query from '{original_query}' to '{enhanced_query}'")
            elif tool_name == "get_projects_list":
                result = VectorSearchClient.get_projects_list()
            elif tool_name == "get_document_types":
                result = VectorSearchClient.get_document_types()
            elif tool_name == "get_search_strategies":
                result = VectorSearchClient.get_search_strategies()
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            logger.info(f"🤖 AGENT: Tool '{tool_name}' executed successfully")
            return {"success": True, "result": result}
            
        except Exception as e:
            logger.error(f"🤖 AGENT: Error executing tool '{tool_name}': {e}")
            return {"success": False, "error": str(e)}

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

    def generate_tool_suggestions(self, query: str) -> List[Dict[str, Any]]:
        """Generate tool suggestions using LLM analysis of the query.
        
        Args:
            query: The user query to analyze
            
        Returns:
            List of suggested tools to improve the API
        """
        if not self.llm_client:
            logger.info("🤖 TOOL SUGGESTIONS: No LLM client available, skipping tool suggestions")
            return []
        
        tools_context = self._format_tools_for_llm()
        
        suggestion_prompt = f"""You are an API design expert analyzing a user query to suggest missing tools.

USER QUERY: "{query}"

CURRENT AVAILABLE TOOLS:
{tools_context}

TASK: Analyze the query and suggest up to 3 NEW tools that would improve the API's capabilities for this type of query.

FOCUS AREAS:
- Temporal/date filtering (if query involves time/dates)
- Geographic/location filtering (if query involves location)
- Advanced search capabilities
- Data aggregation and statistics
- Document metadata and classification

For each suggested tool, provide:
1. function_name: Clear, descriptive name
2. description: What the tool does
3. endpoint: Suggested API endpoint
4. justification: Why this tool would help with the query
5. priority: HIGH/MEDIUM/LOW based on impact
6. parameters: Expected input parameters

Respond with a JSON array of tool suggestions:
[
  {{{{
    "function_name": "tool_name",
    "description": "what it does",
    "endpoint": "/api/suggested/endpoint",
    "justification": "why it helps with this query",
    "priority": "HIGH|MEDIUM|LOW",
    "parameters": {{{{
      "param1": "description",
      "param2": "description"
    }}}}
  }}}}
]

JSON Response:"""

        try:
            messages = [
                {"role": "system", "content": "You are an expert API designer. Respond with valid JSON only."},
                {"role": "user", "content": suggestion_prompt}
            ]
            
            response = self.llm_client.chat_completion(messages, temperature=0.3, max_tokens=1000)
            
            if response and "choices" in response and response["choices"]:
                content = response["choices"][0]["message"]["content"].strip()
                content_clean = content.replace("```json", "").replace("```", "").strip()
                
                suggestions = json.loads(content_clean)
                logger.info(f"🤖 TOOL SUGGESTIONS: LLM generated {len(suggestions)} tool suggestions")
                return suggestions
            else:
                logger.warning("🤖 TOOL SUGGESTIONS: LLM suggestion generation failed")
                return []
                
        except Exception as e:
            logger.error(f"🤖 TOOL SUGGESTIONS: Error in LLM tool suggestion: {e}")
            return []

    def _enhance_step_parameters(self, original_parameters: Dict[str, Any], context: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
        """Enhance step parameters based on execution context and discovered data.
        
        Args:
            original_parameters: The original parameters from the execution plan
            context: Execution context with discovered IDs and mappings
            tool_name: Name of the tool being executed
            
        Returns:
            Enhanced parameters with discovered IDs where appropriate
        """
        enhanced = original_parameters.copy()
        
        if tool_name == "search":
            # Automatically add discovered project IDs if the search query suggests it needs them
            query = enhanced.get("query", "").lower()
            
            # If query mentions specific project names we have mappings for, add the project IDs
            for project_name, project_id in context["project_name_to_id_mapping"].items():
                if project_name in query and not enhanced.get("project_ids"):
                    enhanced["project_ids"] = [project_id]
                    logger.info(f"🤖 CONTEXT: Auto-added project_id {project_id} for query mentioning '{project_name}'")
            
            # Automatically add discovered document type IDs if query mentions document types we have mappings for
            for doc_type_name, doc_type_id in context["document_type_name_to_id_mapping"].items():
                if doc_type_name in query and not enhanced.get("document_type_ids"):
                    enhanced["document_type_ids"] = [doc_type_id]
                    logger.info(f"🤖 CONTEXT: Auto-added document_type_id {doc_type_id} for query mentioning '{doc_type_name}'")
            
            # If query mentions "letters" or "correspondence" and we have those types, use them
            if not enhanced.get("document_type_ids") and context["discovered_document_type_ids"]:
                if any(term in query for term in ["letter", "correspondence", "memo"]):
                    enhanced["document_type_ids"] = context["discovered_document_type_ids"]
                    logger.info(f"🤖 CONTEXT: Auto-added discovered document_type_ids for letter/correspondence query: {enhanced['document_type_ids']}")
            
            # If we have discovered project IDs and the query seems project-specific, use them
            if context["discovered_project_ids"] and not enhanced.get("project_ids"):
                # Check if query is project-specific
                if any(term in query for term in ["south anderson", "resort", "project"]):
                    enhanced["project_ids"] = context["discovered_project_ids"]
                    logger.info(f"🤖 CONTEXT: Auto-added discovered project_ids: {enhanced['project_ids']}")
            
            # Replace placeholder project_ids with discovered ones
            if "project_ids" in enhanced and isinstance(enhanced["project_ids"], list):
                placeholder_patterns = ["obtained", "project_id_for_", "_id", "previous_step", "discovered", "from_"]
                has_placeholders = any(
                    any(pattern in str(pid).lower() for pattern in placeholder_patterns)
                    for pid in enhanced["project_ids"]
                )
                if has_placeholders and context["discovered_project_ids"]:
                    enhanced["project_ids"] = context["discovered_project_ids"]
                    logger.info(f"🤖 CONTEXT: Replaced placeholder project_ids with discovered: {enhanced['project_ids']}")
            
            # Replace placeholder document_type_ids with discovered ones  
            if "document_type_ids" in enhanced and isinstance(enhanced["document_type_ids"], list):
                logger.info(f"🤖 CONTEXT: Checking document_type_ids for placeholders: {enhanced['document_type_ids']}")
                placeholder_patterns = ["obtained", "type_id", "_id", "previous_step", "discovered", "from_", "letter_type"]
                has_placeholders = any(
                    any(pattern in str(dtid).lower() for pattern in placeholder_patterns)
                    for dtid in enhanced["document_type_ids"]
                )
                logger.info(f"🤖 CONTEXT: Has placeholders: {has_placeholders}, Available discovered IDs: {context['discovered_document_type_ids']}")
                if has_placeholders and context["discovered_document_type_ids"]:
                    enhanced["document_type_ids"] = context["discovered_document_type_ids"]
                    logger.info(f"🤖 CONTEXT: Replaced placeholder document_type_ids with discovered: {enhanced['document_type_ids']}")
                elif has_placeholders:
                    logger.warning(f"🤖 CONTEXT: Found placeholders but no discovered document type IDs available")
            
            # Prioritize user-provided parameters (always take precedence)
            if self.user_project_ids:
                enhanced["project_ids"] = self.user_project_ids
                logger.info(f"🤖 CONTEXT: Using user-provided project_ids: {enhanced['project_ids']}")
            
            if self.user_document_type_ids:
                enhanced["document_type_ids"] = self.user_document_type_ids
                logger.info(f"🤖 CONTEXT: Using user-provided document_type_ids: {enhanced['document_type_ids']}")
        
        return enhanced

    def _update_execution_context(self, context: Dict[str, Any], tool_name: str, tool_result: Dict[str, Any]) -> None:
        """Update execution context with results from the current step.
        
        Args:
            context: Execution context to update
            tool_name: Name of the tool that was executed
            tool_result: Result from the tool execution
        """
        if not tool_result.get("success", False):
            return
            
        result_data = tool_result.get("result")
        
        if tool_name == "get_projects_list" and isinstance(result_data, list):
            # Extract project mappings
            for project in result_data:
                if isinstance(project, dict) and "project_id" in project and "project_name" in project:
                    project_id = project["project_id"]
                    project_name = project["project_name"]
                    context["project_name_to_id_mapping"][project_name.lower()] = project_id
                    
                    # Check if this matches what we're looking for
                    if "south anderson" in project_name.lower():
                        context["discovered_project_ids"].append(project_id)
                        logger.info(f"🤖 CONTEXT: Discovered South Anderson project_id: {project_id}")
        
        elif tool_name == "get_document_types" and isinstance(result_data, list):
            # get_document_types now returns a normalized list like get_projects_list
            logger.info(f"🤖 CONTEXT: Processing get_document_types response with {len(result_data)} items")
            
            for doc_type in result_data:
                if isinstance(doc_type, dict) and "document_type_id" in doc_type and "document_type_name" in doc_type:
                    doc_type_id = doc_type["document_type_id"]
                    doc_type_name = doc_type["document_type_name"]
                    context["document_type_name_to_id_mapping"][doc_type_name.lower()] = doc_type_id
                    logger.info(f"🤖 CONTEXT: Added mapping: '{doc_type_name.lower()}' -> {doc_type_id}")
                    
                    # Check if this is a letter/correspondence type
                    if any(term in doc_type_name.lower() for term in ["letter", "correspondence", "memo", "communication"]):
                        context["discovered_document_type_ids"].append(doc_type_id)
                        logger.info(f"🤖 CONTEXT: Discovered letter/correspondence document_type_id: {doc_type_id} ({doc_type_name})")
                    
                    # Also look for other common document types that might be mentioned in queries
                    for doc_keyword in ["report", "assessment", "study", "plan", "notice", "application", "decision"]:
                        if doc_keyword in doc_type_name.lower():
                            # Don't add to discovered list automatically, but log for context
                            logger.info(f"🤖 CONTEXT: Found {doc_keyword} document type: {doc_type_id} ({doc_type_name})")
            
            logger.info(f"🤖 CONTEXT: Final discovered_document_type_ids: {context['discovered_document_type_ids']}")
        
        elif tool_name == "search" and isinstance(result_data, tuple) and len(result_data) >= 1:
            # Extract project IDs from search results if we don't have any yet
            documents = result_data[0]
            if isinstance(documents, list) and not context["discovered_project_ids"]:
                for doc in documents:
                    if isinstance(doc, dict) and "project_id" in doc:
                        project_id = doc["project_id"]
                        if project_id not in context["discovered_project_ids"]:
                            context["discovered_project_ids"].append(project_id)
                            logger.info(f"🤖 CONTEXT: Discovered project_id from search: {project_id}")


def handle_agent_query(query: str, reason: str, llm_client=None, user_location: Optional[Dict[str, Any]] = None, 
                      project_ids: Optional[List[str]] = None, document_type_ids: Optional[List[str]] = None, 
                      search_strategy: Optional[str] = None, ranking: Optional[Dict[str, Any]] = None) -> dict:
    """Handle agent-required queries with tool execution.
    
    Args:
        query: The complex query that requires agent processing
        reason: Why the query was classified as agent-required
        llm_client: Optional LLM client for intelligent planning
        user_location: Optional user location data from request body
        project_ids: Optional user-provided project IDs to respect in agent search calls
        document_type_ids: Optional user-provided document type IDs to respect in agent search calls
        search_strategy: Optional user-provided search strategy to use in agent search calls
        ranking: Optional user-provided ranking configuration to use in agent search calls
        
    Returns:
        Dict with agent processing results and any tool executions
    """
    
    logger.info("=" * 60)
    logger.info("🤖 AGENT MODE ACTIVATED")
    logger.info(f"Query: {query}")
    logger.info(f"Reason: {reason}")
    
    # Validate that LLM client is provided (required for agent mode)
    if not llm_client:
        logger.error("🤖 AGENT: LLM client is required for agent mode")
        return {
            "error": "Agent mode requires LLM client for intelligent planning",
            "agent_results": [],
            "planning_method": "Failed - No LLM client",
            "execution_time": 0,
            "steps_executed": 0,
            "consolidated_summary": "Error: LLM client not provided for agent mode"
        }
    
    logger.info("LLM Planning: Enabled")
    if project_ids:
        logger.info(f"User-provided project IDs: {project_ids}")
    if document_type_ids:
        logger.info(f"User-provided document type IDs: {document_type_ids}")
    if search_strategy:
        logger.info(f"User-provided search strategy: {search_strategy}")
    if ranking:
        logger.info(f"User-provided ranking: {ranking}")
    logger.info("=" * 60)
    
    try:
        # Initialize agent with user location and provided parameters
        agent = VectorSearchAgent(
            llm_client=llm_client, 
            user_location=user_location,
            project_ids=project_ids,
            document_type_ids=document_type_ids,
            search_strategy=search_strategy,
            ranking=ranking
        )
        
        # Generate tool suggestions first (LLM-based analysis)
        logger.info("🤖 AGENT: Generating LLM-based tool suggestions...")
        tool_suggestions = agent.generate_tool_suggestions(query)
        logger.info(f"🤖 AGENT: Generated {len(tool_suggestions)} tool suggestions")
        
        # Create execution plan using LLM
        execution_plan = agent.create_execution_plan(query, reason)
        
        logger.info(f"🤖 AGENT: Execution plan created with {len(execution_plan)} steps")
        
        # Execute the plan with context passing between steps
        results = []
        all_documents = []
        all_document_chunks = []
        execution_context = {
            "discovered_project_ids": [],
            "discovered_document_type_ids": [],
            "project_name_to_id_mapping": {},
            "document_type_name_to_id_mapping": {}
        }
        
        for i, step in enumerate(execution_plan):
            # Check if this step is redundant based on current context
            if agent._should_skip_step(step, execution_context):
                logger.info(f"🤖 AGENT: Skipping redundant step {i+1}: {step['step_name']}")
                results.append({
                    "step": step["step_name"],
                    "tool": step["tool"],
                    "parameters": step["parameters"],
                    "original_parameters": step["parameters"],
                    "reasoning": step.get("reasoning", ""),
                    "result": {"success": True, "result": "Skipped - information already available", "skipped": True}
                })
                continue
            
            # Enhance parameters based on previous step results
            enhanced_parameters = agent._enhance_step_parameters(step["parameters"], execution_context, step["tool"])
            
            # Execute with enhanced parameters
            tool_result = agent.execute_tool(step["tool"], enhanced_parameters)
            
            # Update execution context with results
            agent._update_execution_context(execution_context, step["tool"], tool_result)
            
            # Extract documents and chunks from tool results and prepare clean result for storage
            clean_tool_result = tool_result.copy()
            
            if tool_result.get("success", False) and "result" in tool_result:
                tool_data = tool_result["result"]
                
                # The VectorSearchClient.search returns (documents, api_response) tuple
                # For search tools, store only the first element (documents/chunks) to avoid duplication
                if step["tool"] == "search" and isinstance(tool_data, tuple) and len(tool_data) >= 1:
                    documents_or_chunks = tool_data[0]  # First element is the documents/chunks list
                    
                    # Store only the clean documents array, not the full tuple
                    clean_tool_result["result"] = documents_or_chunks
                    
                    if isinstance(documents_or_chunks, list):
                        for item in documents_or_chunks:
                            if isinstance(item, dict):
                                # If it has chunk-specific fields, it's a chunk
                                if 'chunk_text' in item or 'chunk_content' in item or 'content' in item:
                                    all_document_chunks.append(item)
                                # Otherwise treat as document
                                else:
                                    all_documents.append(item)
                # For non-search tools, keep the result as-is
            
            # Store the result with enhanced parameters for tracking (using clean result for search tools)
            results.append({
                "step": step["step_name"],
                "tool": step["tool"],
                "parameters": enhanced_parameters,  # Use enhanced parameters
                "original_parameters": step["parameters"],  # Keep original for comparison
                "reasoning": step.get("reasoning", ""),
                "result": clean_tool_result  # Use clean result (no tuple duplication for search)
            })
        
        logger.info(f"🤖 AGENT: Completed {len(results)} tool executions")
        logger.info(f"🤖 AGENT: Consolidated {len(all_documents)} documents and {len(all_document_chunks)} chunks")
        
        # Analyze results for summary
        successful_executions = [r for r in results if r["result"].get("success", False)]
        failed_executions = [r for r in results if not r["result"].get("success", False)]
        
        logger.info(f"🤖 AGENT: {len(successful_executions)} successful, {len(failed_executions)} failed executions")
        
        logger.info("=" * 60)
        
        return {
            "agent_attempted": True,
            "agent_implemented": True,
            "query": query,
            "reason": reason,
            "planning_method": "LLM-driven",
            "execution_plan": execution_plan,
            "tool_executions": results,
            "agent_success": len(failed_executions) == 0,
            "tool_suggestions": tool_suggestions,  # LLM-generated suggestions
            "consolidated_results": {
                "documents": all_documents,
                "document_chunks": all_document_chunks,
                "total_documents": len(all_documents),
                "total_chunks": len(all_document_chunks)
            },
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
