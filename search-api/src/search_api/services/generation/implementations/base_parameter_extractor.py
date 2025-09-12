"""
Base Parameter Extractor Implementation
Contains common logic for parameter extraction approach.
"""
import json
import logging
from typing import Dict, List, Optional, Any

from search_api.services.generation.abstractions.parameter_extractor import ParameterExtractor

logger = logging.getLogger(__name__)

class BaseParameterExtractor(ParameterExtractor):
    """Base implementation of parameter extractor with common logic."""
    
    def __init__(self, client):
        self.client = client
    
    def extract_parameters(
        self,
        query: str,
        available_projects: Optional[Dict] = None,
        available_document_types: Optional[Dict] = None,
        available_strategies: Optional[Dict] = None,
        supplied_project_ids: Optional[List[str]] = None,
        supplied_document_type_ids: Optional[List[str]] = None,
        supplied_search_strategy: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract search parameters using focused, sequential calls.
        
        Args:
            query: The natural language search query.
            available_projects: Dict of available projects {name: id}.
            available_document_types: Dict of available document types with aliases.
            available_strategies: Dict of available search strategies.
            supplied_project_ids: Already provided project IDs (skip LLM extraction if provided).
            supplied_document_type_ids: Already provided document type IDs (skip LLM extraction if provided).
            supplied_search_strategy: Already provided search strategy (skip LLM extraction if provided).
            
        Returns:
            Dict containing extracted parameters.
        """
        try:
            logger.info("Starting multi-step parameter extraction")
            
            # Step 1: Extract project IDs (skip if already provided)
            if supplied_project_ids:
                project_ids = supplied_project_ids
                logger.info(f"Step 1 - Using supplied project IDs: {project_ids}")
            else:
                project_ids = self._extract_project_ids(query, available_projects)
                logger.info(f"Step 1 - Extracted project IDs: {project_ids}")
            
            # Step 2: Extract document type IDs (skip if already provided)
            if supplied_document_type_ids:
                document_type_ids = supplied_document_type_ids
                logger.info(f"Step 2 - Using supplied document type IDs: {document_type_ids}")
            else:
                document_type_ids = self._extract_document_types(query, available_document_types)
                logger.info(f"Step 2 - Extracted document type IDs: {document_type_ids}")
            
            # Step 3: Extract search strategy (skip if already provided)
            if supplied_search_strategy:
                search_strategy = supplied_search_strategy
                logger.info(f"Step 3 - Using supplied search strategy: {search_strategy}")
            else:
                search_strategy = self._extract_search_strategy(query, available_strategies)
                logger.info(f"Step 3 - Extracted search strategy: {search_strategy}")
            
            # Step 4: Extract/optimize semantic query (usually always run for query optimization)
            semantic_query = self._extract_semantic_query(query, project_ids, document_type_ids)
            logger.info(f"Step 4 - Optimized semantic query: {semantic_query}")
            
            # Combine results
            return {
                "project_ids": project_ids,
                "document_type_ids": document_type_ids,
                "search_strategy": search_strategy,
                "semantic_query": semantic_query,
                "confidence": 0.8,
                "extraction_sources": {
                    "project_ids": "supplied" if supplied_project_ids else "llm_extracted",
                    "document_type_ids": "supplied" if supplied_document_type_ids else "llm_extracted",
                    "search_strategy": "supplied" if supplied_search_strategy else "llm_extracted",
                    "semantic_query": "llm_optimized"
                }
            }
            
        except Exception as e:
            logger.error(f"Multi-step parameter extraction failed: {e}")
            return self._fallback_extraction(query, available_projects, available_document_types, available_strategies, supplied_project_ids, supplied_document_type_ids, supplied_search_strategy)
    
    def _extract_project_ids(self, query: str, available_projects: Optional[Dict] = None) -> List[str]:
        """Extract project IDs from query using focused LLM call."""
        if not available_projects:
            return []
        
        try:
            prompt = f"""You are a project ID extraction specialist. Find project references in the query and match them to available project IDs.

Available Projects:
{chr(10).join([f"- {name}: {project_id}" for name, project_id in available_projects.items()])}

Instructions:
- Look for project names, abbreviations, or partial matches in the query
- Use fuzzy matching - "South Anderson Mountain Resort" might match "South Anderson Mountain" or "Anderson Mountain Resort"
- Look for keywords like "Resort", "Mountain", "Anderson", etc.
- If you find partial matches or related terms, include those projects
- Return project IDs (not names) that are mentioned or clearly relevant
- Be inclusive - better to return a potentially relevant project than miss it

Query: "{query}"

Think through this step by step:
1. What project-related terms do I see in the query?
2. Which available projects might match those terms?
3. What are the IDs for those matching projects?

Return the matching project IDs as a JSON array of strings."""

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response["choices"][0]["message"]["content"].strip()
            
            # Try to parse JSON response
            try:
                if content.startswith('[') and content.endswith(']'):
                    project_ids = json.loads(content)
                    # Validate that returned IDs are actually available
                    valid_ids = [pid for pid in project_ids if pid in available_projects.values()]
                    return valid_ids
                else:
                    # Fallback: look for project mentions in text
                    return self._fallback_project_extraction(query, available_projects)
            except json.JSONDecodeError:
                return self._fallback_project_extraction(query, available_projects)
                
        except Exception as e:
            logger.warning(f"Project ID extraction failed: {e}")
            return self._fallback_project_extraction(query, available_projects)
    
    def _extract_document_types(self, query: str, available_document_types: Optional[Dict] = None) -> List[str]:
        """Extract document type IDs from query using focused LLM call."""
        if not available_document_types:
            return []
        
        try:
            # Build comprehensive document type info including aliases
            doc_context = []
            for doc_id, doc_data in available_document_types.items():
                name = doc_data.get('name', 'Unknown')
                aliases = doc_data.get('aliases', [])
                alias_text = f" (aliases: {', '.join(aliases)})" if aliases else ""
                doc_context.append(f"- {name}{alias_text} (ID: {doc_id})")
            
            prompt = f"""You are a document type identification specialist. Find document type references in the query and match them to available document type IDs.

Available Document Types:
{chr(10).join(doc_context)}

Instructions:
- Look for document type names, aliases, or related terms in the query
- Search ALL aliases for each document type - if the query mentions any alias, include that document type
- Look for both exact matches and partial matches
- "letters" should match both "Letter to Minister" and "Letter from Minister" document types
- "correspondence" might match letter types
- "reports" might match various report types
- Be inclusive - if there's any reasonable match, include the document type
- Return document type IDs (not names) for ALL relevant matches
- If user asks for "all documents" or doesn't specify, return empty array
- Maximum 5 document type IDs

Query: "{query}"

Think through this step by step:
1. What document-related terms do I see in the query?
2. Which document types or aliases match those terms?
3. What are ALL the IDs for matching document types?

Return ALL matching document type IDs as a JSON array of strings."""

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response["choices"][0]["message"]["content"].strip()
            
            # Try to parse JSON response
            try:
                if content.startswith('[') and content.endswith(']'):
                    doc_type_ids = json.loads(content)
                    # Validate that returned IDs are actually available and limit to 5
                    valid_ids = [dtid for dtid in doc_type_ids if dtid in available_document_types.keys()][:5]
                    return valid_ids
                else:
                    return self._fallback_document_extraction(query, available_document_types)
            except json.JSONDecodeError:
                return self._fallback_document_extraction(query, available_document_types)
                
        except Exception as e:
            logger.warning(f"Document type extraction failed: {e}")
            return self._fallback_document_extraction(query, available_document_types)
    
    def _extract_search_strategy(self, query: str, available_strategies: Optional[Dict] = None) -> str:
        """Extract search strategy using focused LLM call."""
        try:
            strategies_list = list(available_strategies.keys()) if available_strategies else ["HYBRID_PARALLEL", "SEMANTIC_ONLY", "KEYWORD_ONLY"]
            
            prompt = f"""You are a search strategy specialist. Determine the best search strategy for this query.

Available Strategies: {', '.join(strategies_list)}

Instructions:
- PREFER "HYBRID_PARALLEL" unless very confident another strategy is better
- Use "KEYWORD_ONLY" only if user asks for exact term matching
- Use "SEMANTIC_ONLY" only if user asks for conceptual/thematic search

Query: "{query}"

Return ONLY the strategy name (e.g., "HYBRID_PARALLEL")"""

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response["choices"][0]["message"]["content"].strip().replace('"', '')
            
            # Validate strategy
            if content in strategies_list:
                return content
            else:
                return "HYBRID_PARALLEL"
                
        except Exception as e:
            logger.warning(f"Search strategy extraction failed: {e}")
            return "HYBRID_PARALLEL"

    def _extract_semantic_query(self, query: str, project_ids: List[str] = None, document_type_ids: List[str] = None) -> str:
        """Extract and optimize semantic query using focused LLM call."""
        try:
            prompt = f"""You are a semantic query optimization specialist. Extract the core search concepts from this query.

Instructions:
- Extract ONLY the core search concepts, remove project names and document type references
- Keep semantic query concise (2-6 key terms)
- Focus on the subject matter, not the metadata filters
- Preserve important entity names and specific terms

Examples:
- "letters mentioning Nooaitch Indian Band" → "Nooaitch Indian Band"
- "environmental impact of water quality" → "environmental impact water quality"
- "permits for forestry project" → "forestry permits"
- "correspondence about Lower Similkameen Indian Band" → "Lower Similkameen Indian Band correspondence"

Original Query: "{query}"

Return ONLY the optimized semantic query (no quotes, no explanation)"""

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response["choices"][0]["message"]["content"].strip().replace('"', '')
            
            # Basic validation - should be shorter and meaningful
            if len(content) > 0 and len(content) < len(query) * 1.5:
                return content
            else:
                return query
                
        except Exception as e:
            logger.warning(f"Semantic query extraction failed: {e}")
            return query
    
    def _fallback_project_extraction(self, query: str, available_projects: Dict) -> List[str]:
        """Fallback project extraction using fuzzy keyword matching."""
        query_lower = query.lower()
        matched_projects = []
        
        for project_name, project_id in available_projects.items():
            project_name_lower = project_name.lower()
            
            # Check for exact match
            if project_name_lower in query_lower:
                matched_projects.append(project_id)
                continue
            
            # Check for fuzzy matching - split project name into words and see if any appear in query
            project_words = project_name_lower.split()
            for word in project_words:
                if len(word) > 3 and word in query_lower:  # Only check meaningful words
                    matched_projects.append(project_id)
                    break
        
        return matched_projects
    
    def _fallback_document_extraction(self, query: str, available_document_types: Dict) -> List[str]:
        """Fallback document type extraction using comprehensive alias matching."""
        query_lower = query.lower()
        matched_types = []
        
        for doc_id, doc_data in available_document_types.items():
            name = doc_data.get('name', '').lower()
            aliases = [alias.lower() for alias in doc_data.get('aliases', [])]
            
            # Check name
            if name and any(word in query_lower for word in name.split() if len(word) > 3):
                matched_types.append(doc_id)
                continue
            
            # Check all aliases - look for any that contain query terms or vice versa
            for alias in aliases:
                if alias in query_lower or any(term in alias for term in query_lower.split() if len(term) > 3):
                    matched_types.append(doc_id)
                    break
        
        return matched_types[:5]  # Limit to 5
    
    
    def _fallback_extraction(self, query: str, available_projects: Optional[Dict] = None, 
                           available_document_types: Optional[Dict] = None,
                           available_strategies: Optional[Dict] = None,
                           supplied_project_ids: Optional[List[str]] = None,
                           supplied_document_type_ids: Optional[List[str]] = None,
                           supplied_search_strategy: Optional[str] = None) -> Dict[str, Any]:
        """Complete fallback extraction."""
        return {
            "project_ids": supplied_project_ids or self._fallback_project_extraction(query, available_projects or {}),
            "document_type_ids": supplied_document_type_ids or self._fallback_document_extraction(query, available_document_types or {}),
            "search_strategy": supplied_search_strategy or "HYBRID_PARALLEL",
            "semantic_query": query,
            "confidence": 0.2,
            "extraction_sources": {
                "project_ids": "supplied" if supplied_project_ids else "fallback",
                "document_type_ids": "supplied" if supplied_document_type_ids else "fallback",
                "search_strategy": "supplied" if supplied_search_strategy else "fallback",
                "semantic_query": "fallback"
            }
        }
    
    def _make_llm_call(self, messages: List[Dict], temperature: float = 0.1) -> Dict[str, Any]:
        """Make LLM call - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _make_llm_call method")