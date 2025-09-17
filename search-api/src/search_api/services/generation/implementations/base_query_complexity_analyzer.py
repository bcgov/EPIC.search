"""Base implementation for query complexity analysis."""

import json
import logging
from typing import Dict, Any, List
from ..abstractions.query_complexity_analyzer import QueryComplexityAnalyzer
from ....clients.vector_search_client import VectorSearchClient

logger = logging.getLogger(__name__)


class BaseQueryComplexityAnalyzer(QueryComplexityAnalyzer):
    """Base implementation for 3-tier query complexity analysis using LLM."""
    
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
    
    def analyze_complexity(self, query: str) -> Dict[str, Any]:
        """Single LLM call to determine query complexity tier."""
        
        logger.info("=== QUERY COMPLEXITY ANALYSIS START ===")
        logger.info(f"Query to analyze: '{query}'")
        
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

{project_guidance}

{doc_type_guidance}

CLASSIFICATION RULES:

🟢 SIMPLE (only if ALL conditions met):
- Contains ONE specific project name (from available list if provided)
- Contains ONE specific document type (from available list if provided)
- Does NOT contain multiple projects
- Does NOT contain time periods or dates
- Does NOT contain comparison words

🟡 COMPLEX (if ANY condition met):
- Multiple projects mentioned OR vague project names like "mountain projects" 
- Complex logic with AND/OR/NOT/BUT NOT
- Multiple document types
- Broad searches like "anything related to"
- Cross-references between projects
- Mentions entities that are NOT in the available projects list as projects

🔴 AGENT_REQUIRED (if ANY condition met):  
- Contains dates or time periods: "before 2020", "last 5 years", "over time"
- Comparison words: "compare", "versus", "similar projects"
- Trend analysis: "trends", "evolution", "patterns over time"
- Conditional logic: "if project had", "when conditions"

CRITICAL ANALYSIS:
Look for these keywords in "{query}":
- Time words (years, before, after, during, trends) → AGENT_REQUIRED
- Comparison words (compare, versus, across, similar) → AGENT_REQUIRED  
- Multiple projects or entities not in project list → COMPLEX
- AND/OR/NOT/BUT logic → COMPLEX
- Specific project + specific document type → SIMPLE

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
                tier = result.get("complexity_tier", "complex")
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
                    r'similar projects', r'across projects'
                ]
                
                agent_detected = any(re.search(pattern, query_lower) for pattern in agent_patterns)
                logger.info(f"Agent keywords detected: {agent_detected}")
                if agent_detected and tier == "simple":
                    logger.info(f"Rule-based correction: detected agent keywords, upgrading from {tier} to agent_required")
                    tier = "agent_required"
                
                # Check for complex keywords (using word boundaries)
                complex_patterns = [
                    r'\bbut not\b', r'\band not\b', r'\bor\b(?!\w)', r'\bmultiple\b', 
                    r'\bvarious\b', r'\bseveral\b', r'mountain projects', 
                    r'all projects', r'any projects', r'anything related'
                ]
                
                complex_detected = any(re.search(pattern, query_lower) for pattern in complex_patterns)
                logger.info(f"Complex keywords detected: {complex_detected}")
                if complex_detected and tier == "simple":
                    logger.info(f"Rule-based correction: detected complex keywords, upgrading from {tier} to complex")
                    tier = "complex"
                
                final_result = {
                    "complexity_tier": tier,
                    "reason": result.get("reason", "No reason provided"),
                    "confidence": result.get("confidence", 0.5)
                }
                
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
    
    def _make_llm_call(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Dict[str, Any]:
        """Make LLM call. To be implemented by concrete classes."""
        raise NotImplementedError("Subclasses must implement _make_llm_call")