"""
Base Parameter Extractor Implementation
Contains common logic for parameter extraction approach.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        available_projects: Optional[List] = None,
        available_document_types: Optional[List] = None,
        available_strategies: Optional[Dict] = None,
        supplied_project_ids: Optional[List[str]] = None,
        supplied_document_type_ids: Optional[List[str]] = None,
        supplied_search_strategy: Optional[str] = None,
        user_location: Optional[Dict] = None,
        supplied_location: Optional[Dict] = None,
        supplied_project_status: Optional[str] = None,
        supplied_years: Optional[list] = None,
        use_parallel: bool = True
    ) -> Dict[str, Any]:
        """Extract search parameters using parallel or sequential approach.
        
        Args:
            query: The natural language search query.
            available_projects: List of available projects from VectorSearchClient.get_projects_list().
            available_document_types: List of available document types from VectorSearchClient.get_document_types().
            available_strategies: Dict of available search strategies.
            supplied_project_ids: Already provided project IDs (skip LLM extraction if provided).
            supplied_document_type_ids: Already provided document type IDs (skip LLM extraction if provided).
            supplied_search_strategy: Already provided search strategy (skip LLM extraction if provided).
            user_location: User's location data for location-aware queries.
            supplied_location: Already provided location parameter (skip LLM extraction if provided).
            supplied_project_status: Already provided project status (skip LLM extraction if provided).
            supplied_years: Already provided years list (skip LLM extraction if provided).
            use_parallel: Whether to use parallel execution (default: True).
            
        Returns:
            Dict containing extracted parameters including temporal parameters.
        """
        logger.info("=== PARAMETER EXTRACTION START ===")
        logger.info(f"Query to extract from: '{query}'")
        logger.info(f"Use parallel execution: {use_parallel}")
        
        # Log available context data - SHOW ALL DATA (no truncation)
        logger.info("=== AVAILABLE CONTEXT DATA ===")
        if available_projects:
            logger.info(f"Available Projects Array ({len(available_projects)}):")
            for project in available_projects:  # Show ALL projects
                if isinstance(project, dict) and 'project_name' in project and 'project_id' in project:
                    logger.info(f"  - '{project['project_name']}' -> {project['project_id']}")
        else:
            logger.info("Available Projects: None provided")
            
        if available_document_types:
            logger.info(f"Available Document Types Array ({len(available_document_types)}):")
            for doc_type in available_document_types:  # Show ALL document types
                if isinstance(doc_type, dict) and 'document_type_id' in doc_type:
                    name = doc_type.get('document_type_name', 'Unknown')
                    aliases = doc_type.get('aliases', [])
                    logger.info(f"  - '{name}' (ID: {doc_type['document_type_id']}) - Aliases: {aliases}")
        else:
            logger.info("Available Document Types: None provided")
            
        if available_strategies:
            logger.info(f"Available Strategies ({len(available_strategies)}):")
            for name, description in available_strategies.items():
                logger.info(f"  - '{name}': {description}")
        else:
            logger.info("Available Strategies: None provided")
            
        # Log supplied parameters
        logger.info("=== SUPPLIED PARAMETERS ===")
        logger.info(f"Supplied Project IDs: {supplied_project_ids}")
        logger.info(f"Supplied Document Type IDs: {supplied_document_type_ids}")
        logger.info(f"Supplied Search Strategy: {supplied_search_strategy}")
        logger.info(f"User Location: {user_location}")
        logger.info(f"Supplied Location: {supplied_location}")
        logger.info(f"Supplied Project Status: {supplied_project_status}")
        logger.info(f"Supplied Years: {supplied_years}")
        logger.info("=== END CONTEXT DATA ===")
        
        # Convert arrays to dict format for internal processing
        projects_dict = self._convert_projects_array_to_dict(available_projects)
        document_types_dict = self._convert_document_types_array_to_dict(available_document_types)
        
        if use_parallel:
            try:
                return self._extract_parameters_parallel(
                    query, projects_dict, document_types_dict, available_strategies,
                    supplied_project_ids, supplied_document_type_ids, supplied_search_strategy,
                    user_location, supplied_location, supplied_project_status, supplied_years
                )
            except Exception as e:
                logger.warning(f"Parallel extraction failed, falling back to sequential: {e}")
                return self._extract_parameters_sequential(
                    query, projects_dict, document_types_dict, available_strategies,
                    supplied_project_ids, supplied_document_type_ids, supplied_search_strategy,
                    user_location, supplied_location, supplied_project_status, supplied_years
                )
        else:
            return self._extract_parameters_sequential(
                query, projects_dict, document_types_dict, available_strategies,
                supplied_project_ids, supplied_document_type_ids, supplied_search_strategy,
                user_location, supplied_location, supplied_project_status, supplied_years
            )
    
    def _extract_parameters_sequential(
        self,
        query: str,
        available_projects: Optional[Dict] = None,
        available_document_types: Optional[Dict] = None,
        available_strategies: Optional[Dict] = None,
        supplied_project_ids: Optional[List[str]] = None,
        supplied_document_type_ids: Optional[List[str]] = None,
        supplied_search_strategy: Optional[str] = None,
        user_location: Optional[Dict] = None,
        supplied_location: Optional[Dict] = None,
        supplied_project_status: Optional[str] = None,
        supplied_years: Optional[list] = None
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
            logger.info("Starting sequential parameter extraction")
            
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
            semantic_query = self._extract_semantic_query(query)
            logger.info(f"Step 4 - Optimized semantic query: {semantic_query}")
            
            # Step 5: Extract temporal parameters (location, project_status, years) using LLM
            if supplied_location is not None or supplied_project_status is not None or supplied_years is not None:
                # Use supplied temporal parameters
                location = supplied_location
                project_status = supplied_project_status
                years = supplied_years
                logger.info(f"Step 5 - Using supplied temporal parameters: location={location}, status={project_status}, years={years}")
                temporal_sources = {
                    "location": "supplied" if supplied_location is not None else "fallback",
                    "project_status": "supplied" if supplied_project_status is not None else "fallback", 
                    "years": "supplied" if supplied_years is not None else "fallback"
                }
            else:
                # Extract temporal parameters using LLM
                temporal_result = self._extract_temporal_parameters(query, user_location)
                location = temporal_result.get("location")
                project_status = temporal_result.get("project_status")
                years = temporal_result.get("years", [])
                logger.info(f"Step 5 - Extracted temporal parameters: location={location}, status={project_status}, years={years}")
                temporal_sources = {
                    "location": "llm_extracted" if location is not None else "fallback",
                    "project_status": "llm_extracted" if project_status is not None else "fallback",
                    "years": "llm_extracted" if years else "fallback"
                }
            
            # Combine results
            return {
                "project_ids": project_ids,
                "document_type_ids": document_type_ids,
                "search_strategy": search_strategy,
                "semantic_query": semantic_query,
                "location": location,
                "project_status": project_status,
                "years": years,
                "confidence": 0.8,
                "extraction_sources": {
                    "project_ids": "supplied" if supplied_project_ids else "llm_sequential",
                    "document_type_ids": "supplied" if supplied_document_type_ids else "llm_sequential",
                    "search_strategy": "supplied" if supplied_search_strategy else "llm_sequential",
                    "semantic_query": "llm_sequential",
                    **temporal_sources
                }
            }
            
        except Exception as e:
            logger.error(f"Sequential parameter extraction failed: {e}")
            return self._fallback_extraction(query, available_projects, available_document_types, available_strategies, supplied_project_ids, supplied_document_type_ids, supplied_search_strategy)
            
        except Exception as e:
            logger.error(f"Multi-step parameter extraction failed: {e}")
            return self._fallback_extraction(query, available_projects, available_document_types, available_strategies, supplied_project_ids, supplied_document_type_ids, supplied_search_strategy)
    
    def _extract_parameters_parallel(
        self,
        query: str,
        available_projects: Optional[Dict] = None,
        available_document_types: Optional[Dict] = None,
        available_strategies: Optional[Dict] = None,
        supplied_project_ids: Optional[List[str]] = None,
        supplied_document_type_ids: Optional[List[str]] = None,
        supplied_search_strategy: Optional[str] = None,
        user_location: Optional[Dict] = None,
        supplied_location: Optional[Dict] = None,
        supplied_project_status: Optional[str] = None,
        supplied_years: Optional[list] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Extract search parameters using parallel LLM calls for maximum speed.
        
        Args:
            query: The natural language search query.
            available_projects: Dict of available projects {name: id}.
            available_document_types: Dict of available document types with aliases.
            available_strategies: Dict of available search strategies.
            supplied_project_ids: Already provided project IDs (skip LLM extraction if provided).
            supplied_document_type_ids: Already provided document type IDs (skip LLM extraction if provided).
            supplied_search_strategy: Already provided search strategy (skip LLM extraction if provided).
            timeout: Timeout in seconds for parallel execution.
            
        Returns:
            Dict containing extracted parameters.
        """
        try:
            logger.info("Starting parallel parameter extraction")
            
            # Prepare tasks for parallel execution
            tasks = []
            task_names = []
            
            # Task 1: Extract project IDs (if not supplied)
            if not supplied_project_ids:
                tasks.append(lambda: self._extract_project_ids(query, available_projects))
                task_names.append("project_ids")
            
            # Task 2: Extract document type IDs (if not supplied)
            if not supplied_document_type_ids:
                tasks.append(lambda: self._extract_document_types(query, available_document_types))
                task_names.append("document_type_ids")
            
            # Task 3: Extract search strategy (if not supplied)
            if not supplied_search_strategy:
                tasks.append(lambda: self._extract_search_strategy(query, available_strategies))
                task_names.append("search_strategy")
            
            # Task 4: Extract semantic query (always run for optimization)
            tasks.append(lambda: self._extract_semantic_query(query))
            task_names.append("semantic_query")
            
            # Task 5: Extract temporal parameters (if not supplied)
            if supplied_location is None or supplied_project_status is None or supplied_years is None:
                tasks.append(lambda: self._extract_temporal_parameters(query, user_location))
                task_names.append("temporal_parameters")
            
            # Execute tasks in parallel using ThreadPoolExecutor
            results = {}
            
            if tasks:
                with ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as executor:
                    # Submit all tasks
                    future_to_name = {
                        executor.submit(task): name 
                        for task, name in zip(tasks, task_names)
                    }
                    
                    # Collect results with timeout
                    for future in as_completed(future_to_name, timeout=timeout):
                        task_name = future_to_name[future]
                        try:
                            result = future.result()
                            results[task_name] = result
                            logger.info(f"Parallel task '{task_name}' completed: {result}")
                        except Exception as e:
                            logger.warning(f"Parallel task '{task_name}' failed: {e}")
                            # Use fallback for failed task
                            results[task_name] = self._get_fallback_for_task(
                                task_name, query, available_projects, 
                                available_document_types, available_strategies
                            )
            
            # Extract temporal parameters from results or use supplied values
            temporal_result = results.get("temporal_parameters", {})
            location = supplied_location if supplied_location is not None else temporal_result.get("location")
            project_status = supplied_project_status if supplied_project_status is not None else temporal_result.get("project_status")
            years = supplied_years if supplied_years is not None else temporal_result.get("years", [])
            
            # Combine results with supplied values
            return {
                "project_ids": supplied_project_ids or results.get("project_ids", []),
                "document_type_ids": supplied_document_type_ids or results.get("document_type_ids", []),
                "search_strategy": supplied_search_strategy or results.get("search_strategy", "HYBRID_PARALLEL"),
                "semantic_query": results.get("semantic_query", query),
                "location": location,
                "project_status": project_status,
                "years": years,
                "confidence": 0.8,
                "extraction_sources": {
                    "project_ids": "supplied" if supplied_project_ids else "llm_parallel",
                    "document_type_ids": "supplied" if supplied_document_type_ids else "llm_parallel",
                    "search_strategy": "supplied" if supplied_search_strategy else "llm_parallel",
                    "semantic_query": "llm_parallel",
                    "location": "supplied" if supplied_location is not None else ("llm_parallel" if location is not None else "fallback"),
                    "project_status": "supplied" if supplied_project_status is not None else ("llm_parallel" if project_status is not None else "fallback"),
                    "years": "supplied" if supplied_years is not None else ("llm_parallel" if years else "fallback")
                }
            }
            
        except Exception as e:
            logger.error(f"Parallel parameter extraction failed: {e}")
            # Fallback to sequential extraction
            logger.info("Falling back to sequential extraction")
            return self._extract_parameters_sequential(
                query, available_projects, available_document_types, available_strategies,
                supplied_project_ids, supplied_document_type_ids, supplied_search_strategy
            )
    
    def _get_fallback_for_task(
        self, 
        task_name: str, 
        query: str, 
        available_projects: Optional[Dict] = None,
        available_document_types: Optional[Dict] = None,
        available_strategies: Optional[Dict] = None
    ) -> Any:
        """Get fallback result for a specific failed task."""
        if task_name == "project_ids":
            return self._fallback_project_extraction(query, available_projects or {})
        elif task_name == "document_type_ids":
            return self._fallback_document_extraction(query, available_document_types or {})
        elif task_name == "search_strategy":
            return "HYBRID_PARALLEL"
        elif task_name == "semantic_query":
            return query
        else:
            return None
    
    def _extract_project_ids(self, query: str, available_projects: Optional[Dict] = None) -> List[str]:
        """Extract project IDs from query using focused LLM call with validation and retry."""
        logger.info("=== PROJECT ID EXTRACTION START ===")
        logger.info(f"Query for project extraction: '{query}'")
        
        if not available_projects:
            logger.warning("No available projects provided - returning empty list")
            logger.info("=== PROJECT ID EXTRACTION END ===")
            return []
        
        logger.info(f"Available projects for matching ({len(available_projects)}):")
        for name, proj_id in available_projects.items():  # Show ALL projects, no truncation
            logger.info(f"  - '{name}' -> {proj_id}")
        
        # Try LLM extraction with validation and retry
        for attempt in range(3):  # Maximum 3 attempts
            try:
                logger.info(f"Attempt {attempt + 1}/3 for project ID extraction")
                result = self._extract_project_ids_single_attempt(query, available_projects, attempt)
                
                # Validate the result quality
                if self._validate_project_extraction_result(query, result, available_projects):
                    logger.info(f"Project extraction successful on attempt {attempt + 1}: {result}")
                    logger.info("=== PROJECT ID EXTRACTION END ===")
                    return result
                else:
                    logger.warning(f"Project extraction attempt {attempt + 1} failed validation, will retry")
                    
            except Exception as e:
                logger.warning(f"Project extraction attempt {attempt + 1} failed with error: {e}")
                if attempt == 2:  # Last attempt
                    logger.error("All LLM attempts failed, using fallback")
                    break
        
        # All attempts failed, use fallback
        logger.warning("LLM project extraction failed all attempts, using fallback method")
        result = self._fallback_project_extraction(query, available_projects)
        logger.info(f"Fallback extraction result: {result}")
        logger.info("=== PROJECT ID EXTRACTION END ===")
        return result
    
    def _extract_project_ids_single_attempt(self, query: str, available_projects: Dict, attempt: int) -> List[str]:
        """Single attempt at project ID extraction with different strategies per attempt."""
        try:
            prompt = f"""You are a project ID extraction specialist. Analyze the query to find the most relevant project names and match them to available project IDs.

Available Projects:
{chr(10).join([f"- {name}: {project_id}" for name, project_id in available_projects.items()])}

IMPORTANT CONTEXT UNDERSTANDING:
- Terms like "Mountain", "River", "Creek", "Lake", "Park", "Resort" are common geographic/facility descriptors
- The DISTINCTIVE part of a project name is usually the specific location name that comes BEFORE or AFTER these descriptors
- For example: "Black Mountain Reservoir" - "Black" is the distinctive identifier, "Mountain Reservoir" is the descriptor
- "Coastal River Project" - "Coastal River" is the distinctive identifier, "Project" is the descriptor

Instructions:
1. Identify the SPECIFIC project name or distinctive location mentioned in the query
2. If the query mentions a complete project name (e.g., "Site C Clean Energy Project"), match ONLY that exact project
3. If the query uses generic terms (e.g., "mountain projects"), look for the complete context to determine which specific mountain project is intended
4. Pay attention to ALL parts of the project name, not just common geographic terms
5. Prefer exact or near-exact matches over broad keyword matches
6. Maximum 3 project IDs unless the query clearly indicates multiple distinct projects are wanted
7. If the query is ambiguous, prefer the most distinctive/complete name matches

Query: "{query}"

Think step by step:
1. What SPECIFIC location or project name is mentioned in the query?
2. Which projects contain this specific location name (not just the generic descriptor)?
3. How confident am I that each match is what the user is actually looking for?

Return as JSON with format:
{{
    "project_matches": [
        {{"project_id": "id1", "project_name": "name1", "confidence": 0.95, "reason": "exact match for complete project name"}},
        {{"project_id": "id2", "project_name": "name2", "confidence": 0.85, "reason": "strong match for distinctive location identifier"}},
        {{"project_id": "id3", "project_name": "name3", "confidence": 0.75, "reason": "partial match for location identifier, but less specific"}}
    ]
}}

Include matches with confidence >= 0.7 and prioritize complete/distinctive name matches over generic descriptor matches"""

            logger.info("=== PROJECT EXTRACTION PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END PROJECT EXTRACTION PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            logger.info("=== PROJECT EXTRACTION LLM RESPONSE ===")
            logger.info(f"Raw LLM Response: {response}")
            
            content = response["choices"][0]["message"]["content"].strip()
            logger.info(f"Content extracted from response: '{content}'")
            logger.info("=== END PROJECT EXTRACTION LLM RESPONSE ===")
            
            # Try to parse JSON response with confidence scores
            try:
                if content.startswith('{') and content.endswith('}'):
                    result = json.loads(content)
                    project_matches = result.get("project_matches", [])
                    
                    logger.info("=== PROJECT MATCHES ANALYSIS ===")
                    logger.info(f"Number of project matches returned: {len(project_matches)}")
                    
                    # Extract project IDs from matches with confidence >= 0.7
                    matched_ids = []
                    for match in project_matches:
                        confidence = match.get("confidence", 0)
                        project_id = match.get("project_id")
                        project_name = match.get("project_name", "")
                        reason = match.get("reason", "")
                        
                        logger.info(f"Match: {project_name} (ID: {project_id}) - Confidence: {confidence} - Reason: {reason}")
                        
                        # Validate project ID exists in available projects
                        if project_id in available_projects.values():
                            logger.info(f"  ✓ Valid project ID found in available projects")
                        else:
                            logger.warning(f"  ✗ Project ID {project_id} NOT found in available projects")
                        
                        # Use higher threshold for better quality matches
                        if confidence >= 0.7 and project_id and project_id in available_projects.values():
                            matched_ids.append(project_id)
                            logger.info(f"  → ACCEPTED: {project_name} added to results")
                        else:
                            logger.info(f"  → REJECTED: Confidence too low ({confidence}) or invalid ID")
                    
                    logger.info(f"Final matched project IDs: {matched_ids}")
                    logger.info("=== END PROJECT MATCHES ANALYSIS ===")
                    logger.info("=== PROJECT ID EXTRACTION END ===")
                    return matched_ids[:3]  # Limit to 3 for more focused results
                    
                elif content.startswith('[') and content.endswith(']'):
                    # Fallback: try old format
                    project_ids = json.loads(content)
                    valid_ids = [pid for pid in project_ids if pid in available_projects.values()]
                    logger.warning(f"Using fallback array format, got {len(valid_ids)} project IDs: {valid_ids}")
                    logger.info("=== PROJECT ID EXTRACTION END ===")
                    return valid_ids[:3]  # Limit to 3 for focused results
                else:
                    logger.warning("LLM response not in expected JSON format, using fallback")
                    result = self._fallback_project_extraction(query, available_projects)
                    logger.info(f"Fallback extraction result: {result}")
                    logger.info("=== PROJECT ID EXTRACTION END ===")
                    return result
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                result = self._fallback_project_extraction(query, available_projects)
                logger.info(f"Fallback extraction result: {result}")
                logger.info("=== PROJECT ID EXTRACTION END ===")
                return result
                
        except Exception as e:
            logger.warning(f"Project ID extraction failed: {e}")
            return self._fallback_project_extraction(query, available_projects)
    
    def _extract_document_types(self, query: str, available_document_types: Optional[Dict] = None) -> List[str]:
        """Extract document type IDs from query using focused LLM call."""
        logger.info("=== DOCUMENT TYPE EXTRACTION START ===")
        logger.info(f"Query for document type extraction: '{query}'")
        
        if not available_document_types:
            logger.warning("No available document types provided - returning empty list")
            logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
            return []
        
        logger.info(f"Available document types for matching ({len(available_document_types)}):")
        for doc_id, doc_data in available_document_types.items():  # Show ALL document types, no truncation
            name = doc_data.get('name', 'Unknown')
            aliases = doc_data.get('aliases', [])
            logger.info(f"  - '{name}' (ID: {doc_id}) - Aliases: {aliases}")
        
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

WHEN TO SELECT DOCUMENT TYPES:
✓ Query explicitly mentions document types: "show me letters", "find reports", "get presentations"
✓ Query asks for specific document format: "correspondence about X", "memos regarding Y"
✓ Query requests specific document categories: "technical reports", "meeting transcripts"

WHEN TO RETURN EMPTY ARRAY [] (search all document types):
✗ General information queries: "who is the proponent?", "what is the project status?"
✗ Factual questions about projects: "when was X approved?", "where is Y located?"
✗ Broad queries: "tell me about project X", "information on Y"
✗ Process questions: "what are the impacts?", "what consultation occurred?"
✗ If user asks for "all documents" or "look at all documents"

Instructions for when document types ARE relevant:
- Look for document type names, aliases, or related terms in the query
- Search ALL aliases for each document type - if the query mentions any alias, include that document type
- Look for both exact matches and partial matches
- "letters" should match both "Letter to Minister" and "Letter from Minister" document types
- "correspondence" might match letter types
- "reports" might match various report types
- Be inclusive - if there's any reasonable match, include the document type
- Return document type IDs (not names) for ALL relevant matches

Query: "{query}"

Think through this step by step:
1. Is this query asking for specific document types, or general information?
2. If asking for general information, return empty array []
3. If asking for specific document types, what document-related terms do I see?
4. Which document types or aliases match those terms?
5. What are ALL the IDs for matching document types?

Return matching document type IDs as a JSON array of strings, or [] if this is a general information query."""

            logger.info("=== DOCUMENT TYPE EXTRACTION PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END DOCUMENT TYPE EXTRACTION PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            logger.info("=== DOCUMENT TYPE EXTRACTION LLM RESPONSE ===")
            logger.info(f"Raw LLM Response: {response}")
            
            content = response["choices"][0]["message"]["content"].strip()
            logger.info(f"Content extracted from response: '{content}'")
            logger.info("=== END DOCUMENT TYPE EXTRACTION LLM RESPONSE ===")
            
            # Try to parse JSON response
            try:
                # Clean up the content and try to parse as JSON
                content_clean = content.strip()
                logger.info(f"Cleaned content for JSON parsing: '{content_clean}'")
                
                # Extract JSON from markdown code blocks if present
                if '```json' in content_clean:
                    # Find the JSON block between ```json and ```
                    start_marker = '```json'
                    end_marker = '```'
                    start_idx = content_clean.find(start_marker)
                    if start_idx != -1:
                        start_idx += len(start_marker)
                        end_idx = content_clean.find(end_marker, start_idx)
                        if end_idx != -1:
                            json_content = content_clean[start_idx:end_idx].strip()
                            logger.info(f"Extracted JSON from markdown blocks: '{json_content}'")
                            content_clean = json_content
                
                # Handle case where LLM provides explanation text followed by JSON array
                elif not content_clean.startswith('[') and not content_clean.startswith('{'):
                    # Look for JSON array at the end of explanation text
                    import re
                    # Find the last JSON array pattern in the content
                    array_matches = re.findall(r'\[(?:[^\[\]]*|\[[^\[\]]*\])*\]', content_clean)
                    if array_matches:
                        content_clean = array_matches[-1].strip()
                        logger.info(f"Extracted JSON array from explanation text: '{content_clean}'")
                
                # Try to parse directly as JSON (handles multiple formats)
                parsed_response = json.loads(content_clean)
                
                # Handle different response formats
                if isinstance(parsed_response, list):
                    # Direct array format: [] or ["id1", "id2"]
                    doc_type_ids = parsed_response
                elif isinstance(parsed_response, dict):
                    # Object format with result key: {"result": []}
                    if "result" in parsed_response:
                        doc_type_ids = parsed_response["result"]
                        logger.info(f"Extracted document type IDs from 'result' key: {doc_type_ids}")
                    else:
                        logger.warning(f"LLM response is dict but no 'result' key found: {parsed_response}")
                        result = self._fallback_document_extraction(query, available_document_types)
                        logger.info(f"Fallback extraction result: {result}")
                        logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                        return result
                else:
                    logger.warning(f"LLM response is not a list or dict, got: {type(parsed_response)}")
                    result = self._fallback_document_extraction(query, available_document_types)
                    logger.info(f"Fallback extraction result: {result}")
                    logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                    return result
                
                # Ensure the final result is a list
                if not isinstance(doc_type_ids, list):
                    logger.warning(f"Document type IDs is not a list after extraction, got: {type(doc_type_ids)}")
                    result = self._fallback_document_extraction(query, available_document_types)
                    logger.info(f"Fallback extraction result: {result}")
                    logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                    return result
                
                logger.info("=== DOCUMENT TYPE MATCHES ANALYSIS ===")
                logger.info(f"LLM returned document type IDs: {doc_type_ids}")
                
                # If empty array, LLM determined no specific document types needed
                if not doc_type_ids:
                    logger.info("LLM returned empty array - no document type filtering needed")
                    logger.info("=== END DOCUMENT TYPE MATCHES ANALYSIS ===")
                    logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                    return []
                
                # Validate that returned IDs are actually available
                valid_ids = []
                for dtid in doc_type_ids:
                    if dtid in available_document_types.keys():
                        doc_name = available_document_types[dtid].get('name', 'Unknown')
                        valid_ids.append(dtid)
                        logger.info(f"  ✓ Valid document type ID: {dtid} -> '{doc_name}'")
                    else:
                        logger.warning(f"  ✗ Invalid document type ID: {dtid} (not found in available types)")
                
                final_ids = valid_ids  # No artificial limit
                logger.info(f"Final document type IDs: {final_ids}")
                logger.info("=== END DOCUMENT TYPE MATCHES ANALYSIS ===")
                logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                return final_ids
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response as JSON: {e}")
                result = self._fallback_document_extraction(query, available_document_types)
                logger.info(f"Fallback extraction result: {result}")
                logger.info("=== DOCUMENT TYPE EXTRACTION END ===")
                return result
                
        except Exception as e:
            logger.warning(f"Document type extraction failed: {e}")
            return self._fallback_document_extraction(query, available_document_types)
    
    def _extract_search_strategy(self, query: str, available_strategies: Optional[Dict] = None) -> str:
        """Extract search strategy using focused LLM call."""
        logger.info("=== SEARCH STRATEGY EXTRACTION START ===")
        logger.info(f"Query for search strategy extraction: '{query}'")
        
        try:
            strategies_list = list(available_strategies.keys()) if available_strategies else ["HYBRID_PARALLEL", "SEMANTIC_ONLY", "KEYWORD_ONLY"]
            
            logger.info(f"Available strategies: {strategies_list}")
            
            prompt = f"""You are a search strategy specialist. Determine the best search strategy for this query.

Available Strategies: {', '.join(strategies_list)}

Instructions:
- PREFER "HYBRID_PARALLEL" unless very confident another strategy is better
- Use "KEYWORD_ONLY" only if user asks for exact term matching
- Use "SEMANTIC_ONLY" only if user asks for conceptual/thematic search

Query: "{query}"

Return ONLY the strategy name (e.g., "HYBRID_PARALLEL")"""

            logger.info("=== SEARCH STRATEGY EXTRACTION PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END SEARCH STRATEGY EXTRACTION PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            logger.info("=== SEARCH STRATEGY EXTRACTION LLM RESPONSE ===")
            logger.info(f"Raw LLM Response: {response}")
            
            content = response["choices"][0]["message"]["content"].strip().replace('"', '')
            logger.info(f"Content extracted from response: '{content}'")
            logger.info("=== END SEARCH STRATEGY EXTRACTION LLM RESPONSE ===")
            
            # Validate strategy
            if content in strategies_list:
                logger.info(f"Strategy '{content}' is valid - using it")
                logger.info("=== SEARCH STRATEGY EXTRACTION END ===")
                return content
            else:
                logger.warning(f"Strategy '{content}' not in available strategies, defaulting to HYBRID_PARALLEL")
                logger.info("=== SEARCH STRATEGY EXTRACTION END ===")
                return "HYBRID_PARALLEL"
                
        except Exception as e:
            logger.warning(f"Search strategy extraction failed: {e}")
            return "HYBRID_PARALLEL"

    def _extract_semantic_query(self, query: str) -> str:
        """Extract and optimize semantic query using focused LLM call."""
        logger.info("=== SEMANTIC QUERY EXTRACTION START ===")
        logger.info(f"Original query for semantic optimization: '{query}'")
        
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

            logger.info("=== SEMANTIC QUERY EXTRACTION PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END SEMANTIC QUERY EXTRACTION PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            logger.info("=== SEMANTIC QUERY EXTRACTION LLM RESPONSE ===")
            logger.info(f"Raw LLM Response: {response}")
            
            content = response["choices"][0]["message"]["content"].strip().replace('"', '')
            logger.info(f"Content extracted from response: '{content}'")
            logger.info("=== END SEMANTIC QUERY EXTRACTION LLM RESPONSE ===")
            
            # Basic validation - should be shorter and meaningful
            if len(content) > 0 and len(content) < len(query) * 1.5:
                logger.info(f"Semantic query optimization successful: '{query}' -> '{content}'")
                logger.info("=== SEMANTIC QUERY EXTRACTION END ===")
                return content
            else:
                logger.warning(f"Semantic query validation failed - content too long or empty, using original query")
                logger.info("=== SEMANTIC QUERY EXTRACTION END ===")
                return query
                
        except Exception as e:
            logger.warning(f"Semantic query extraction failed: {e}")
            logger.info("=== SEMANTIC QUERY EXTRACTION END ===")
            return query
    
    def _fallback_project_extraction(self, query: str, available_projects: Dict) -> List[str]:
        """Enhanced fallback project extraction with focus on distinctive name components."""
        query_lower = query.lower()
        matched_projects = []
        
        # Common geographic/facility descriptors that are less distinctive
        generic_terms = {'mountain', 'river', 'creek', 'lake', 'park', 'resort', 'wind', 'reservoir', 'project'}
        
        for project_name, project_id in available_projects.items():
            project_name_lower = project_name.lower()
            
            # Check for exact match first
            if project_name_lower in query_lower or query_lower in project_name_lower:
                matched_projects.append(project_id)
                continue
            
            # Smart keyword matching - focus on distinctive parts
            project_words = set(project_name_lower.split())
            query_words = set(query_lower.split())
            
            # Filter out common words and generic geographic terms
            distinctive_project_words = project_words - {'the', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'with', 'by'} - generic_terms
            distinctive_query_words = query_words - {'the', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'with', 'by', 'projects'} - generic_terms
            
            # Find matching distinctive words
            distinctive_matches = distinctive_project_words & distinctive_query_words
            
            # Also check for generic terms if there are other supporting matches
            generic_matches = (project_words & generic_terms) & (query_words & generic_terms)
            
            if len(distinctive_matches) > 0:
                # Strong match - has distinctive identifiers
                matched_projects.append(project_id)
            elif len(distinctive_matches) == 0 and len(generic_matches) > 0:
                # Only generic matches - be very selective
                # Only include if the query is very specific and short (likely targeting this type)
                if len(query_words) <= 3 and any(word in project_name_lower for word in query_words if len(word) > 4):
                    matched_projects.append(project_id)
        
        # Limit to 3 for focused results
        return matched_projects[:3]
    
    def _fallback_document_extraction(self, query: str, available_document_types: Dict) -> List[str]:
        """Fallback document type extraction using comprehensive alias matching."""
        logger.info("=== FALLBACK DOCUMENT TYPE EXTRACTION ===")
        query_lower = query.lower()
        
        # Check if this is a general information query that shouldn't filter document types
        general_query_indicators = [
            "who is", "what is", "when was", "where is", "how much", "how many",
            "main proponent", "project status", "tell me about", "information on",
            "what are the impacts", "what consultation", "all documents"
        ]
        
        if any(indicator in query_lower for indicator in general_query_indicators):
            logger.info(f"Query contains general information indicators - returning empty array")
            logger.info("=== END FALLBACK DOCUMENT TYPE EXTRACTION ===")
            return []
        
        # Only do text matching for queries that explicitly mention document types
        document_type_keywords = ["letter", "report", "memo", "correspondence", "transcript", "assessment", "presentation"]
        if not any(keyword in query_lower for keyword in document_type_keywords):
            logger.info(f"Query does not mention specific document types - returning empty array")
            logger.info("=== END FALLBACK DOCUMENT TYPE EXTRACTION ===")
            return []
        
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
        
        logger.info(f"Fallback matched document types: {matched_types}")
        logger.info("=== END FALLBACK DOCUMENT TYPE EXTRACTION ===")
        return matched_types  # Return all matched types
    
    
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
    
    def _extract_temporal_parameters(self, query: str, user_location: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract temporal parameters (location, project_status, years) using LLM reasoning.
        
        Args:
            query: The search query to analyze
            user_location: User's location data for location-aware queries
            
        Returns:
            Dict containing temporal parameters: location, project_status, years
        """
        try:
            from datetime import datetime
            current_year = datetime.now().year
            
            prompt = f"""You are a temporal and geographic parameter extraction specialist. Analyze the following search query to extract:

1. LOCATION PARAMETERS (MUST BE STRING FORMAT):
   - Look for geographic references, location names, or phrases like "near me", "local", "my area"
   - ALWAYS return location as a STRING in format "City, Region" or "Region" (e.g., "Langford, BC", "Peace River region", "Vancouver")
   - If user has provided location data and query contains "near me" or location references, extract the city/region from user location as a STRING
   - If query mentions specific location names, extract those as a STRING
   - DO NOT return location as a JSON object - ONLY strings like "Vancouver, BC" or "Peace River region"

2. PROJECT STATUS:
   - Look for project lifecycle indicators: "active", "completed", "recent", "ongoing", "historical", "current", "past", "future"
   - Map temporal words to appropriate status (e.g., "recently" -> "recent", "ongoing projects" -> "active")

3. TEMPORAL/YEARS:
   - Extract specific years, year ranges, or relative time expressions
   - Current year is {current_year}
   - Map relative terms to concrete years:
     * "recently", "lately" -> last 2-3 years including current [{current_year-2}, {current_year-1}, {current_year}]
     * "last N years" -> calculate range from current year
     * "this year", "current year" -> [{current_year}]
     * "past year" -> [{current_year-1}, {current_year}]
     * "since YYYY" -> range from specified year to current
     * Specific years or ranges -> extract as provided

USER LOCATION CONTEXT: {user_location if user_location else "No user location provided"}

QUERY TO ANALYZE: "{query}"

Respond with ONLY a JSON object in this exact format:
{{
    "location": null_or_string_like_"Vancouver_BC"_or_"Peace_River_region",
    "project_status": null_or_status_string,
    "years": [],
    "reasoning": "explanation of extraction logic",
    "confidence": 0.0_to_1.0
}}

EXAMPLES:
Query: "Show me recent projects near me"
User Location: {{"city": "Langford", "region": "British Columbia"}}
Response: {{"location": "Langford, British Columbia", "project_status": "recent", "years": [{current_year-2}, {current_year-1}, {current_year}], "reasoning": "User wants recent projects in their location - extracted city and region as string", "confidence": 0.9}}

Query: "Environmental reports from 2020-2022 in Peace River region"
Response: {{"location": "Peace River region", "project_status": null, "years": [2020, 2021, 2022], "reasoning": "Specific location and year range provided", "confidence": 0.95}}

Query: "Projects in Vancouver"
Response: {{"location": "Vancouver", "project_status": null, "years": [], "reasoning": "Query explicitly mentions Vancouver", "confidence": 0.95}}"""

            logger.info("=== TEMPORAL EXTRACTION PROMPT ===")
            logger.info(f"Prompt: {prompt}")
            logger.info("=== END TEMPORAL EXTRACTION PROMPT ===")

            response = self._make_llm_call(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response["choices"][0]["message"]["content"].strip()
            logger.info(f"Raw temporal extraction response: {content}")
            
            # Parse JSON response
            result = json.loads(content)
            
            # Validate and clean the response
            temporal_params = {
                "location": result.get("location"),
                "project_status": result.get("project_status"), 
                "years": result.get("years", []),
                "reasoning": result.get("reasoning", ""),
                "confidence": float(result.get("confidence", 0.0))
            }
            
            logger.info(f"Extracted temporal parameters: {temporal_params}")
            return temporal_params
            
        except Exception as e:
            logger.error(f"Error extracting temporal parameters: {e}")
            return {
                "location": None,
                "project_status": None,
                "years": [],
                "reasoning": f"LLM extraction failed: {e}",
                "confidence": 0.0
            }

    def _convert_projects_array_to_dict(self, projects_array: Optional[List]) -> Dict:
        """Convert projects array from VectorSearchClient.get_projects_list() to dict format.
        
        Args:
            projects_array: Array from VectorSearchClient.get_projects_list()
            
        Returns:
            Dict in format {project_name: project_id} for internal processing
        """
        if not projects_array:
            return {}
            
        projects_dict = {}
        if isinstance(projects_array, list):
            for project in projects_array:
                if isinstance(project, dict) and 'project_id' in project and 'project_name' in project:
                    projects_dict[project['project_name']] = project['project_id']
        
        logger.info(f"Converted {len(projects_array) if projects_array else 0} projects array to {len(projects_dict)} projects dict")
        return projects_dict
    
    def _convert_document_types_array_to_dict(self, document_types_array: Optional[List]) -> Dict:
        """Convert document types array from VectorSearchClient.get_document_types() to dict format.
        
        Args:
            document_types_array: Array from VectorSearchClient.get_document_types()
            
        Returns:
            Dict in format {doc_type_id: {name, aliases, act}} for internal processing
        """
        if not document_types_array:
            return {}
            
        document_types_dict = {}
        if isinstance(document_types_array, list):
            for doc_type in document_types_array:
                if isinstance(doc_type, dict) and 'document_type_id' in doc_type:
                    doc_type_id = doc_type['document_type_id']
                    document_types_dict[doc_type_id] = {
                        'name': doc_type.get('document_type_name', ''),
                        'aliases': doc_type.get('aliases', []),
                        'act': doc_type.get('act', '')
                    }
        
        logger.info(f"Converted {len(document_types_array) if document_types_array else 0} document types array to {len(document_types_dict)} document types dict")
        return document_types_dict

    def _make_llm_call(self, messages: List[Dict], temperature: float = 0.1) -> Dict[str, Any]:
        """Make LLM call - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _make_llm_call method")