"""Project inference service for automatically detecting project references in search queries.

This module provides intelligent project detection capabilities that analyze user queries
to identify project names and other project-related entities. When users ask questions 
like "who is the main proponent for the Site C project?", the system can automatically 
infer which project(s) they're referring to and apply appropriate filtering without 
requiring explicit project IDs.

The service includes:
1. Named entity recognition for project names and project-related terms
2. Fuzzy matching against known project names in the projects table
3. Confidence scoring for automatic project inference based solely on project name similarity
4. Integration with the search pipeline for transparent project filtering

Note: Project inference is based exclusively on project names from the projects table,
not on proponent organizations, to ensure focused and accurate project detection.
"""

import re
import logging
import pandas as pd
import psycopg

from flask import current_app
from .vector_store import VectorStore
from typing import List, Tuple, Dict, Any
from difflib import SequenceMatcher

class ProjectInferenceService:
    """Service for inferring project context from natural language queries.
    
    This service analyzes search queries to automatically detect project references
    and provides confident project ID suggestions when users mention specific projects
    by name without explicitly providing project IDs. Inference is based exclusively
    on project names from the projects table for focused and accurate matching.
    """
    
    def __init__(self):
        """Initialize the project inference service."""
        self.vector_store = VectorStore()
        self._project_cache = None
        self._cache_timestamp = None
        self.cache_ttl = 300  # 5 minutes cache TTL
    
    def infer_projects_from_query(self, query: str, confidence_threshold: float = 0.8) -> Tuple[List[str], float, Dict[str, Any]]:
        """Infer project IDs from a natural language query based on project names.
        
        Analyzes the query for project names and project-related terminology to suggest 
        relevant project IDs with confidence scoring. Matching is performed exclusively 
        against project names from the projects table.
        
        Args:
            query (str): The natural language search query
            confidence_threshold (float): Minimum confidence required for automatic inference (default: 0.8)
            
        Returns:
            tuple: A tuple containing:
                - List[str]: Inferred project IDs (empty if confidence too low)
                - float: Confidence score (0.0 to 1.0)
                - Dict[str, Any]: Inference metadata including matched entities and reasoning
        """
        inference_metadata = {
            "extracted_entities": [],
            "matched_projects": [],
            "reasoning": [],
            "method": "entity_matching"
        }
        
        try:
            # Extract potential project entities from the query
            entities = self._extract_project_entities(query)
            inference_metadata["extracted_entities"] = entities
            
            if not entities:
                logging.info(f"No project entities extracted from query: '{query}'")
                return [], 0.0, inference_metadata
            
            # Get available projects (with caching)
            projects_df = self._get_projects_cached()
            
            if projects_df.empty:
                logging.warning("No projects found in database for inference")
                return [], 0.0, inference_metadata
            
            # Match entities against known projects
            matched_projects = self._match_entities_to_projects(entities, projects_df)
            inference_metadata["matched_projects"] = matched_projects
            
            # Calculate confidence and select projects
            project_ids, confidence = self._calculate_confidence_and_select_projects(
                matched_projects, confidence_threshold
            )
            
            # Add reasoning to metadata
            if project_ids:
                inference_metadata["reasoning"] = [
                    f"Detected entity '{match['entity']}' matching project '{match['project_name']}' with similarity {match['similarity']:.3f}"
                    for match in matched_projects if match["project_id"] in project_ids
                ]
                logging.info(f"Project inference successful: {len(project_ids)} projects with confidence {confidence:.3f}")
            else:
                inference_metadata["reasoning"] = [
                    f"Confidence {confidence:.3f} below threshold {confidence_threshold}"
                ]
                logging.info(f"Project inference below confidence threshold: {confidence:.3f} < {confidence_threshold}")
            
            return project_ids, confidence, inference_metadata
            
        except Exception as e:
            logging.error(f"Error in project inference: {e}")
            inference_metadata["error"] = str(e)
            return [], 0.0, inference_metadata
    
    def _extract_project_entities(self, query: str) -> List[str]:
        """Extract potential project names from the query.
        
        Focuses on extracting project names rather than organization names,
        using patterns that identify project-specific terminology.
        
        Args:
            query (str): The search query text
            
        Returns:
            List[str]: List of extracted entities that might be project names
        """
        entities = []
        
        # Convert to lowercase for processing
        query_lower = query.lower()
        
        # Pattern 1: Project names with explicit project-related terms
        # "BC Hydro project", "Trans Mountain pipeline", "Site C dam", etc.
        project_patterns = [
            r'\b([A-Z][a-zA-Z\s&]+(?:project|pipeline|development|proposal|application|mine|dam|terminal|facility))\b',
            r'\b([A-Z][a-zA-Z\s&]+)\s+(?:project|pipeline|development|proposal|application|mine|dam|terminal|facility)\b',
            r'\bthe\s+([A-Z][a-zA-Z\s&]+)\s+(?:project|pipeline|development|proposal|application|mine|dam|terminal|facility)\b'
        ]
        
        for pattern in project_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend([match.strip() for match in matches])
        
        # Pattern 2: Standalone capitalized project names
        # Look for capitalized phrases that could be project names
        # But exclude common non-project words
        standalone_pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,2})\b'
        standalone_matches = re.findall(standalone_pattern, query)
        
        # Filter out common English words and very generic terms
        excluded_words = {
            'The', 'Project', 'Development', 'Company', 'Corporation', 'Inc', 'Ltd',
            'Environmental', 'Impact', 'Assessment', 'Report', 'Study', 'Management',
            'British Columbia', 'Government', 'Ministry', 'Department', 'Agency'
        }
        
        for match in standalone_matches:
            words = match.split()
            # Only include if it's not all excluded words and has some substance
            if not any(word in excluded_words for word in words) and len(words) >= 2:
                entities.append(match.strip())
        
        # Pattern 3: Quoted project names
        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted_matches = re.findall(quoted_pattern, query)
        entities.extend([match.strip() for match in quoted_matches])
        
        # Remove duplicates and short entities
        entities = list(set([entity for entity in entities if len(entity) > 3]))
        
        logging.debug(f"Extracted project entities from '{query}': {entities}")
        return entities
    
    def _get_projects_cached(self) -> pd.DataFrame:
        """Get all projects with caching for performance.
        
        Queries only the projects table and retrieves only project_id and project_name
        for project inference matching based solely on project names.
        
        Returns:
            pd.DataFrame: DataFrame containing project_id and project_name columns
        """
        import time
        current_time = time.time()
        
        # Check if cache is valid
        if (self._project_cache is not None and 
            self._cache_timestamp is not None and
            current_time - self._cache_timestamp < self.cache_ttl):
            return self._project_cache
        
        # Refresh cache
        try:
            with psycopg.connect(current_app.vector_settings.database_url) as conn:
                with conn.cursor() as cursor:
                    # Query the projects table directly for project inference
                    # Only retrieve project_id and project_name for name-based matching
                    query = """
                    SELECT DISTINCT 
                        project_id,
                        project_name
                    FROM projects 
                    WHERE project_id IS NOT NULL 
                        AND project_name IS NOT NULL
                        AND project_name != ''
                    ORDER BY project_name;
                    """
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    columns = ["project_id", "project_name"]
                    self._project_cache = pd.DataFrame(results, columns=columns)
                    self._cache_timestamp = current_time
                    
                    logging.debug(f"Cached {len(self._project_cache)} projects from projects table")
                    return self._project_cache
                    
        except Exception as e:
            logging.error(f"Error fetching projects for inference: {e}")
            # Return empty DataFrame on error
            self._project_cache = pd.DataFrame(columns=["project_id", "project_name"])
            return self._project_cache
    
    def _match_entities_to_projects(self, entities: List[str], projects_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Match extracted entities to known projects using fuzzy matching on project names only.
        
        This method performs matching based solely on project names, not proponent organizations,
        to provide focused and accurate project inference based on direct project references.
        
        Args:
            entities (List[str]): List of extracted entity strings
            projects_df (pd.DataFrame): DataFrame with project_id and project_name columns
            
        Returns:
            List[Dict[str, Any]]: List of matches with similarity scores based on project name matching
        """
        matches = []
        
        for entity in entities:
            entity_lower = entity.lower()
            
            for _, project in projects_df.iterrows():
                project_name = str(project.get("project_name", "")).lower()
                
                # Skip empty names
                if not project_name or project_name == "nan":
                    continue
                
                # Calculate similarity score for project name only
                name_similarity = SequenceMatcher(None, entity_lower, project_name).ratio()
                
                # Check for partial matches and exact substring matches
                if entity_lower in project_name or project_name in entity_lower:
                    name_similarity = max(name_similarity, 0.9)
                
                # Only include matches above a minimum threshold
                if name_similarity > 0.6:
                    matches.append({
                        "entity": entity,
                        "project_id": project["project_id"],
                        "project_name": project["project_name"],
                        "similarity": name_similarity,
                        "match_type": "name"
                    })
        
        # Sort by similarity score (highest first)
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        logging.debug(f"Found {len(matches)} project name matches")
        return matches
    
    def _calculate_confidence_and_select_projects(
        self, 
        matches: List[Dict[str, Any]], 
        confidence_threshold: float
    ) -> Tuple[List[str], float]:
        """Calculate overall confidence and select project IDs.
        
        Args:
            matches (List[Dict[str, Any]]): List of project matches with similarity scores
            confidence_threshold (float): Minimum confidence required
            
        Returns:
            Tuple[List[str], float]: Selected project IDs and confidence score
        """
        if not matches:
            return [], 0.0
        
        # Group matches by project_id and take the highest similarity for each project
        project_scores = {}
        for match in matches:
            project_id = match["project_id"]
            if project_id not in project_scores or match["similarity"] > project_scores[project_id]["similarity"]:
                project_scores[project_id] = match
        
        # Calculate overall confidence based on top matches
        top_matches = sorted(project_scores.values(), key=lambda x: x["similarity"], reverse=True)
        
        if not top_matches:
            return [], 0.0
        
        # Simple confidence calculation: average of top similarities, weighted by number of matches
        top_similarities = [match["similarity"] for match in top_matches[:3]]  # Top 3 matches
        confidence = sum(top_similarities) / len(top_similarities)
        
        # Apply bonus for very high similarity matches
        if top_similarities[0] > 0.9:
            confidence = min(1.0, confidence * 1.1)
        
        # Select projects if confidence meets threshold
        if confidence >= confidence_threshold:
            # For high confidence, return top project(s)
            if confidence > 0.9 and len(top_matches) >= 1:
                # Very confident - return top match only
                selected_projects = [top_matches[0]["project_id"]]
            elif confidence > 0.8 and len(top_matches) >= 2:
                # Moderately confident - return top 2 if both are strong
                selected_projects = [
                    match["project_id"] for match in top_matches[:2] 
                    if match["similarity"] > 0.7
                ]
            else:
                # Lower confidence - return only the best match
                selected_projects = [top_matches[0]["project_id"]]
            
            return selected_projects, confidence
        else:
            return [], confidence


# Global instance for easy access
project_inference_service = ProjectInferenceService()
