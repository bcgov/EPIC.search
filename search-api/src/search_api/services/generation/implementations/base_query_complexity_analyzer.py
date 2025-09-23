"""Base implementation for query complexity analysis."""

import json
import logging
from typing import Dict, Any, List, Optional
from ..abstractions.query_complexity_analyzer import QueryComplexityAnalyzer
from ....clients.vector_search_client import VectorSearchClient
from ....utils.cache import cache_with_ttl

logger = logging.getLogger(__name__)


class BaseQueryComplexityAnalyzer(QueryComplexityAnalyzer):
    """Base implementation for 3-tier query complexity analysis using LLM."""
    
    @cache_with_ttl(ttl_seconds=86400)  # Cache for 24 hours (86400 seconds)
    def _fetch_available_options(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Fetch available projects and document types from vector search API.
        
        Returns:
            tuple: (available_projects, available_document_types) dictionaries
        """
        available_projects = {}
        available_document_types = {}
        
        try:
            # Get available projects from vector search API
            available_projects_list = VectorSearchClient.get_projects_list()
            for project in available_projects_list:
                if isinstance(project, dict) and 'project_name' in project and 'project_id' in project:
                    available_projects[project['project_name']] = project['project_id']
            
            logger.info(f"🧠 COMPLEXITY: Found {len(available_projects)} available projects")
            
        except Exception as e:
            logger.warning(f"🧠 COMPLEXITY: Could not fetch projects: {e}")
            # No fallback - work without project context
        
        try:
            # Get available document types from vector search API
            document_types_data = VectorSearchClient.get_document_types()
            
            if isinstance(document_types_data, dict) and document_types_data:
                available_document_types = document_types_data.get('document_types', {})
                logger.info(f"🧠 COMPLEXITY: Found {len(available_document_types)} available document types")
                
        except Exception as e:
            logger.warning(f"🧠 COMPLEXITY: Could not fetch document types: {e}")
            # No fallback - work without document type context
        
        return available_projects, available_document_types
    
    def analyze_complexity(self, query: str, project_ids: Optional[List[str]] = None, 
                         document_type_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Single LLM call to determine query complexity tier."""
        
        logger.info("=== QUERY COMPLEXITY ANALYSIS START ===")
        logger.info(f"Query to analyze: '{query}'")
        logger.info(f"Request context - Project IDs: {project_ids}")
        logger.info(f"Request context - Document Type IDs: {document_type_ids}")
        
        # Check if we have sufficient context for SIMPLE classification
        has_project_context = project_ids and len(project_ids) > 0
        has_doc_type_context = document_type_ids and len(document_type_ids) > 0
        
        logger.info(f"Context analysis - Has projects: {has_project_context}, Has doc types: {has_doc_type_context}")
        
        try:
            # Fetch available projects and document types for context
            available_projects, available_document_types = self._fetch_available_options()
            
            logger.info("=== COMPLEXITY ANALYSIS CONTEXT ===")
            logger.info(f"Available projects count: {len(available_projects)}")
            if available_projects:
                logger.info("Sample available projects:")
                for name, proj_id in list(available_projects.items())[:5]:
                    logger.info(f"  - '{name}' -> {proj_id}")
                if len(available_projects) > 5:
                    logger.info(f"  ... and {len(available_projects) - 5} more projects")
            
            logger.info(f"Available document types count: {len(available_document_types)}")
            if available_document_types:
                logger.info("Sample available document types:")
                for name, doc_id in list(available_document_types.items())[:5]:
                    logger.info(f"  - '{name}' -> {doc_id}")
                if len(available_document_types) > 5:
                    logger.info(f"  ... and {len(available_document_types) - 5} more document types")
            logger.info("=== END COMPLEXITY ANALYSIS CONTEXT ===")
            
            # Create context strings for the prompt
            if available_projects:
                project_names = list(available_projects.keys())
                project_context = ", ".join(project_names)  # NO TRUNCATION - send all projects
                project_guidance = f"AVAILABLE PROJECTS: {project_context}\n- Only queries mentioning these exact project names should be considered for SIMPLE classification"
            else:
                project_guidance = "AVAILABLE PROJECTS: Unable to fetch project list\n- Use general project name patterns for classification"
            
            if available_document_types:
                # Build document type context with names AND aliases for better matching
                doc_type_context_parts = []
                for doc_id, doc_data in available_document_types.items():
                    name = doc_data.get('name', 'Unknown')
                    aliases = doc_data.get('aliases', [])
                    alias_text = f" (aliases: {', '.join(aliases)})" if aliases else ""
                    doc_type_context_parts.append(f"{name}{alias_text}")
                
                doc_type_context = ", ".join(doc_type_context_parts)  # NO TRUNCATION - send all document types with names
                doc_type_guidance = f"AVAILABLE DOCUMENT TYPES: {doc_type_context}\n- Only queries mentioning these exact document type names or aliases should be considered for SIMPLE classification"
            else:
                doc_type_guidance = "AVAILABLE DOCUMENT TYPES: Unable to fetch document types list\n- Use general document type patterns for classification"
            
            prompt = f"""CRITICAL: You must classify this query into exactly ONE category using the available context.

Query to classify: "{query}"

REQUEST CONTEXT (from UI):
- Project IDs selected: {project_ids if has_project_context else 'None'}
- Document Type IDs selected: {document_type_ids if has_doc_type_context else 'None'}

{project_guidance}

{doc_type_guidance}

CLASSIFICATION RULES:

🟢 SIMPLE (if ANY condition met):
- Project IDs are provided in request context (UI selection) AND query is basic content search
- Document Type IDs are provided in request context (UI selection) AND query is basic content search
- Contains ONE specific project name (from available list) AND no temporal/comparison elements
- Contains ONE specific document type (from available list) AND project context provided
- Basic content searches like "documents mentioning X" that can be handled by RAG engine alone
- Most entity searches where the query can be passed directly to vector search without parameter extraction

🟡 COMPLEX (NLP parameter extraction required):
- Need to extract project names from unstructured text and map to project IDs
- Need to extract document type names from vague references like "environmental docs" → specific doc types
- Need to parse complex entity relationships from natural language
- Need to resolve ambiguous entity references using NLP (e.g., "the big pipeline project" → specific project)
- Queries where we must use NLP to fill in missing parameters that can't be directly mapped
- Entity searches where the query mentions entities that need to be resolved to system parameters

🔴 AGENT_REQUIRED (if ANY condition met):  
- Contains dates or time periods: "before 2020", "last 5 years", "over time"
- Comparison words: "compare", "versus", "similar projects"
- Trend analysis: "trends", "evolution", "patterns over time"
- Conditional logic: "if project had", "when conditions"
- Location analysis: "looking for project near me", "within 10 miles of", "nearby projects"
- Complex logic with AND/OR/NOT/BUT NOT operations
- Multiple projects mentioned OR vague project names like "mountain projects"
- Cross-references between projects requiring analysis
- Broad searches like "anything related to" requiring context understanding

CRITICAL ANALYSIS:
Look for these keywords in "{query}":
- Time words (years, before, after, during, trends) → AGENT_REQUIRED
- Comparison words (compare, versus, across, similar) → AGENT_REQUIRED  
- Multiple projects or entities referenced AS PROJECTS → COMPLEX
- AND/OR/NOT/BUT logic → COMPLEX
- Specific project + specific document type → SIMPLE
- Content search patterns ("mention", "about", "contain", "discuss") → Usually SIMPLE/COMPLEX, NOT agent_required

IMPORTANT: Distinguish between:
- "Show me Project X" (entity AS project) vs "documents mentioning X" (entity AS content)
- Content searches should NOT trigger AGENT_REQUIRED unless they have temporal/comparison elements

EXAMPLES:
- "I want all letters that mention the 'Nooaitch Indian Band'" + project IDs provided → SIMPLE (content search with project context)
- "I want all letters that mention the 'Nooaitch Indian Band'" + document type IDs provided → SIMPLE (content search with doc type context)
- "documents about First Nations consultation" + project IDs OR doc type IDs provided → SIMPLE (content search with UI context)
- "I want all letters that mention the 'Nooaitch Indian Band'" + no UI context → SIMPLE (content search can be handled by RAG)
- "Show me environmental docs for the pipeline project" → COMPLEX (need NLP to map "environmental docs" to specific doc types and "pipeline project" to project ID)
- "the big LNG project near Prince George" → COMPLEX (need NLP to resolve "big LNG project" to specific project)
- "Compare environmental impacts across projects" → AGENT_REQUIRED (comparison)
- "Documents from before 2020" → AGENT_REQUIRED (temporal)
- "LNG Canada project environmental reports" → SIMPLE (if project + doc type both in lists)
- "anything related to First Nations" → AGENT_REQUIRED (broad search requiring context understanding)

JSON response only:
{{
    "complexity_tier": "simple",
    "reason": "Contains specific project and document type",
    "confidence": 0.9
}}"""

            logger.info("=== COMPLEXITY ANALYSIS PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END COMPLEXITY ANALYSIS PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            logger.info("=== COMPLEXITY ANALYSIS LLM RESPONSE ===")
            logger.info(f"Raw LLM Response: {response}")
            
            content = response["choices"][0]["message"]["content"].strip()
            logger.info(f"Content extracted from response: '{content}'")
            logger.info("=== END COMPLEXITY ANALYSIS LLM RESPONSE ===")
            
            # Log the raw response to help debug parsing issues
            logger.info(f"Raw LLM response for complexity analysis: {content}")
            
            # Handle empty or very short responses
            if not content or len(content) < 10:
                logger.warning(f"LLM returned empty or very short response: '{content}'")
                logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
                return {"complexity_tier": "complex", "reason": "Empty LLM response", "confidence": 0.0}
            
            # Try to extract JSON from response if it contains extra text
            content_clean = content
            
            # Look for JSON object markers
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                content_clean = content[start:end]
                logger.info(f"Extracted JSON portion: {content_clean}")
            else:
                logger.warning(f"No JSON object markers found in response: '{content}'")
                logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
                return {"complexity_tier": "complex", "reason": "No JSON in response", "confidence": 0.0}
            
            try:
                result = json.loads(content_clean)
                
                # Validate that we got required fields
                if not isinstance(result, dict) or "complexity_tier" not in result:
                    logger.warning(f"Invalid JSON structure: missing complexity_tier")
                    logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
                    return {"complexity_tier": "complex", "reason": "Invalid JSON structure", "confidence": 0.0}
                
                logger.info("=== COMPLEXITY ANALYSIS RESULT VALIDATION ===")
                tier = result.get("complexity_tier", "complex").lower()
                reason = result.get("reason", "No reason provided")
                confidence = result.get("confidence", 0.5)
                
                logger.info(f"Initial LLM classification: {tier}")
                logger.info(f"Reason: {reason}")
                logger.info(f"Confidence: {confidence}")
                
                # Validate response and apply rule-based corrections
                if tier not in ["simple", "complex", "agent_required"]:
                    logger.warning(f"Invalid tier '{tier}', defaulting to complex")
                    tier = "complex"
                
                # Apply rule-based corrections for obvious patterns
                import re
                query_lower = query.lower()
                
                logger.info("Applying rule-based validation...")
                
                # Check for agent-required keywords (using word boundaries for accuracy)
                agent_patterns = [
                    r'\bcompare\b', r'\bcomparison\b', r'\bversus\b', r'\bvs\b',
                    r'\btrend\b', r'\btrends\b', r'over time', r'\bbefore\b', 
                    r'\bafter\b', r'\bsince\b', r'\byears?\b', r'\bevolution\b', 
                    r'\bevolved\b', r'\bpattern\b', r'\bpatterns\b', 
                    r'similar projects', r'across projects', r'\bbut not\b', 
                    r'\band not\b', r'mountain projects', r'all projects', 
                    r'any projects', r'anything related', r'\bmultiple projects\b'
                ]
                
                agent_detected = any(re.search(pattern, query_lower) for pattern in agent_patterns)
                logger.info(f"Agent keywords detected: {agent_detected}")
                if agent_detected and tier in ["simple", "complex"]:
                    logger.info(f"Rule-based correction: detected agent keywords, upgrading from {tier} to agent_required")
                    tier = "agent_required"
                
                # Check for complex keywords - requiring NLP parameter extraction
                complex_patterns = [
                    r'environmental docs?', r'the .+ project', r'pipeline project',
                    r'big .+ project', r'near .+', r'show me .+ project',
                    r'environmental .+ for', r'reports? for the'
                ]
                
                complex_detected = any(re.search(pattern, query_lower) for pattern in complex_patterns)
                logger.info(f"Complex keywords detected (NLP extraction needed): {complex_detected}")
                if complex_detected and tier == "simple":
                    logger.info(f"Rule-based correction: detected NLP extraction needs, upgrading from {tier} to complex")
                    tier = "complex"
                
                final_result = {
                    "complexity_tier": tier,
                    "reason": result.get("reason", "No reason provided"),
                    "confidence": result.get("confidence", 0.5)
                }
                
                # Add function suggestions if agent mode required
                if tier == "agent_required":
                    logger.info("💡 COMPLEXITY: Agent mode required - generating function suggestions...")
                    function_suggestions = self._generate_function_suggestions(query, final_result)
                    final_result["function_suggestions"] = function_suggestions
                    
                    if function_suggestions:
                        logger.info(f"💡 COMPLEXITY: Generated {len(function_suggestions)} function suggestions")
                        for i, suggestion in enumerate(function_suggestions, 1):
                            logger.info(f"💡 SUGGESTION {i} ({suggestion.get('priority', 'UNKNOWN')} priority):")
                            logger.info(f"   Function: {suggestion.get('function_name', 'unnamed')}")
                            logger.info(f"   Purpose: {suggestion.get('description', 'No description')}")
                            logger.info(f"   Endpoint: {suggestion.get('endpoint', 'Unknown')}")
                            logger.info(f"   Why needed: {suggestion.get('justification', 'No justification')}")
                    else:
                        logger.info("💡 COMPLEXITY: No function suggestions generated")
                else:
                    final_result["function_suggestions"] = []
                
                logger.info(f"Final complexity classification: {tier}")
                logger.info("=== END COMPLEXITY ANALYSIS RESULT VALIDATION ===")
                logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
                
                return final_result
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse complexity analysis. Raw content: '{content}', Cleaned: '{content_clean}', Error: {e}")
                logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
                return {"complexity_tier": "complex", "reason": "JSON parsing failed", "confidence": 0.0}
                
        except Exception as e:
            logger.warning(f"Query complexity analysis failed: {e}")
            logger.info("=== QUERY COMPLEXITY ANALYSIS END ===")
            return {"complexity_tier": "complex", "reason": "Analysis failed", "confidence": 0.0}
    
    def _generate_function_suggestions(self, query: str, complexity_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate function suggestions for complex queries requiring agent capabilities."""
        try:
            logger.info("💡 FUNCTION SUGGESTIONS: Starting generation...")
            logger.info(f"💡 FUNCTION SUGGESTIONS: Query: '{query}'")
            logger.info(f"💡 FUNCTION SUGGESTIONS: Complexity tier: {complexity_result.get('complexity_tier')}")
            
            # Build the prompt for function suggestions
            function_suggestions_prompt = f"""You are an expert API designer analyzing a complex search query that requires agent-level capabilities.

QUERY: "{query}"

COMPLEXITY ANALYSIS:
- Tier: {complexity_result.get('complexity_tier', 'unknown')}
- Reason: {complexity_result.get('reason', 'No reason provided')}
- Confidence: {complexity_result.get('confidence', 0.0)}

CURRENT VECTOR SEARCH CLIENT CAPABILITIES:
The VectorSearchClient currently has these methods:
- search(): Basic vector similarity search
- get_document_similarity(): Document-to-document similarity 
- get_projects(): List available projects
- get_document_types(): List document types for a project
- get_project_statistics(): Get project stats
- health_check(): API health status
- get_analytics(): Basic analytics

TASK: Suggest up to 3 NEW functions that should be added to VectorSearchClient to better handle this type of query.

For each suggestion, provide:
1. function_name: The method name (snake_case)
2. description: What the function does (1 sentence)
3. endpoint: The likely API endpoint path
4. justification: Why this function is needed for this query (1 sentence)
5. priority: HIGH, MEDIUM, or LOW

Focus on metadata queries, advanced filtering, temporal analysis, project management, or specialized search capabilities that would make this query easier to handle.

Respond with valid JSON only:
{{
  "suggestions": [
    {{
      "function_name": "method_name",
      "description": "What it does",
      "endpoint": "/api/path",
      "justification": "Why needed for this query",
      "priority": "HIGH|MEDIUM|LOW"
    }}
  ]
}}"""

            messages = [
                {"role": "system", "content": "You are an expert API designer. Respond with valid JSON only."},
                {"role": "user", "content": function_suggestions_prompt}
            ]
            
            logger.info("💡 FUNCTION SUGGESTIONS: Making LLM call...")
            # Make the LLM call with higher token limit for detailed suggestions
            llm_response = self._make_llm_call(messages, temperature=0.2, max_tokens=800)
            logger.info(f"💡 FUNCTION SUGGESTIONS: LLM response received: {type(llm_response)}")
            
            if not llm_response or "choices" not in llm_response or not llm_response["choices"]:
                logger.warning(f"💡 FUNCTION SUGGESTIONS: No valid LLM response - response: {llm_response}")
                return []
            
            content = llm_response["choices"][0]["message"]["content"].strip()
            logger.info(f"💡 FUNCTION SUGGESTIONS: Raw LLM content (first 200 chars): '{content[:200]}...'")
            
            # Clean and parse the JSON response
            content_clean = content.replace("```json", "").replace("```", "").strip()
            logger.info(f"💡 FUNCTION SUGGESTIONS: Cleaned content (first 200 chars): '{content_clean[:200]}...'")
            
            try:
                suggestions_data = json.loads(content_clean)
                logger.info(f"💡 FUNCTION SUGGESTIONS: JSON parsed successfully: {type(suggestions_data)}")
                suggestions = suggestions_data.get("suggestions", [])
                logger.info(f"💡 FUNCTION SUGGESTIONS: Found {len(suggestions)} raw suggestions")
                
                # Validate and limit to 3 suggestions
                valid_suggestions = []
                for i, suggestion in enumerate(suggestions[:3]):  # Limit to 3
                    logger.info(f"💡 FUNCTION SUGGESTIONS: Validating suggestion {i+1}: {suggestion}")
                    required_fields = ["function_name", "description", "endpoint", "justification", "priority"]
                    missing_fields = [field for field in required_fields if field not in suggestion]
                    
                    if missing_fields:
                        logger.warning(f"💡 FUNCTION SUGGESTIONS: Missing required fields {missing_fields} in suggestion {i+1}: {suggestion}")
                        continue
                    
                    # Validate priority
                    if suggestion["priority"] not in ["HIGH", "MEDIUM", "LOW"]:
                        logger.warning(f"💡 FUNCTION SUGGESTIONS: Invalid priority '{suggestion['priority']}' in suggestion {i+1}, skipping")
                        continue
                        
                    valid_suggestions.append(suggestion)
                    logger.info(f"💡 FUNCTION SUGGESTIONS: Suggestion {i+1} validated successfully")
                
                logger.info(f"💡 FUNCTION SUGGESTIONS: Generated {len(valid_suggestions)} valid suggestions out of {len(suggestions)} total")
                return valid_suggestions
                
            except json.JSONDecodeError as e:
                logger.warning(f"💡 FUNCTION SUGGESTIONS: Failed to parse JSON response.")
                logger.warning(f"💡 FUNCTION SUGGESTIONS: Raw content: '{content}'")
                logger.warning(f"💡 FUNCTION SUGGESTIONS: Cleaned content: '{content_clean}'")
                logger.warning(f"💡 FUNCTION SUGGESTIONS: JSON Error: {e}")
                return []
                
        except Exception as e:
            logger.error(f"💡 FUNCTION SUGGESTIONS: Generation failed with exception: {e}")
            logger.error(f"💡 FUNCTION SUGGESTIONS: Exception type: {type(e)}")
            import traceback
            logger.error(f"💡 FUNCTION SUGGESTIONS: Traceback: {traceback.format_exc()}")
            return []

    def _make_llm_call(self, messages: List[Dict[str, str]], temperature: float = 0.1, max_tokens: int = 200) -> Dict[str, Any]:
        """Make LLM call. To be implemented by concrete classes."""
        raise NotImplementedError("Subclasses must implement _make_llm_call")