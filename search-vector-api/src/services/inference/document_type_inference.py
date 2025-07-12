"""Document type inference service for automatically detecting document type references in search queries.

This module provides intelligent document type detection capabilities that analyze user queries
to identify document type names and related terms. When users ask questions like "I am looking 
for the Inspection Record for project X" or "show me the Environmental Assessment reports", 
the system can automatically infer which document type(s) they're referring to and apply 
appropriate filtering.

The service includes:
1. Fuzzy matching against comprehensive document type alias dictionaries
2. Confidence scoring for automatic document type inference
3. Query cleaning to remove identified document type references
4. Integration with the search pipeline for transparent document type filtering
"""

import re
import logging
from typing import List, Tuple, Dict, Any
from difflib import SequenceMatcher

class DocumentTypeInferenceService:
    """Service for inferring document type context from natural language queries.
    
    This service analyzes search queries to automatically detect document type references
    and provides confident document type ID suggestions when users mention specific document
    types by name without explicitly providing document type IDs.
    """
    
    def __init__(self):
        """Initialize the document type inference service."""
        pass
    
    def infer_document_types_from_query(self, query: str, confidence_threshold: float = 0.7) -> Tuple[List[str], float, Dict[str, Any]]:
        """Infer document type IDs from a natural language query.
        
        Analyzes the query for document type names and related terminology to suggest 
        relevant document type IDs with confidence scoring using fuzzy matching against
        comprehensive alias dictionaries.
        
        Args:
            query (str): The natural language search query
            confidence_threshold (float): Minimum confidence required for automatic inference (default: 0.7)
            
        Returns:
            tuple: A tuple containing:
                - List[str]: Inferred document type IDs (empty if confidence too low)
                - float: Confidence score (0.0 to 1.0)
                - Dict[str, Any]: Detailed inference metadata including entities and reasoning
        """
        # Get document type aliases
        try:
            # Import relative to the src root
            import sys
            import os
            src_path = os.path.join(os.path.dirname(__file__), '..', '..')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            
            from utils.document_types import get_all_document_type_aliases
            document_type_aliases = get_all_document_type_aliases()
        except ImportError as e:
            logging.warning(f"Could not import document type aliases: {e}, using empty fallback")
            return [], 0.0, {"error": "Document type aliases not available"}
        
        # Extract potential document type terms from query
        query_lower = query.lower()
        words = re.findall(r'\b\w+\b', query_lower)
        
        # Find matches using fuzzy matching
        matches = []
        
        for type_id, type_info in document_type_aliases.items():
            type_name = type_info["name"]
            aliases = type_info["aliases"]
            
            best_similarity = 0.0
            best_match = None
            match_type = None
            
            # Check for exact matches first (prioritize longer matches)
            # Sort aliases by length (longest first) to get most specific matches
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            for alias in sorted_aliases:
                # Use word boundary matching for exact matches
                pattern = r'\b' + re.escape(alias.lower()) + r'\b'
                if re.search(pattern, query_lower):
                    best_similarity = 1.0
                    best_match = alias
                    match_type = "exact"
                    break
            
            # If no exact match, try fuzzy matching
            if best_similarity < 1.0:
                for word in words:
                    # Skip very short words for fuzzy matching to avoid false positives
                    if len(word) < 4:  # Increased from 3 to 4
                        continue
                        
                    for alias in aliases:
                        # Skip very short aliases for fuzzy matching
                        if len(alias) < 4:  # Increased from 3 to 4
                            continue
                            
                        # Calculate similarity using SequenceMatcher
                        similarity = SequenceMatcher(None, word, alias.lower()).ratio()
                        
                        # For compound terms (containing spaces), only match if the word
                        # matches the entire alias or is very similar
                        if " " in alias:
                            # For compound aliases, require very high similarity or exact word match
                            if word.lower() == alias.lower() or similarity >= 0.95:
                                similarity = 1.0 if word.lower() == alias.lower() else similarity
                            else:
                                continue  # Skip compound aliases for partial matches
                        else:
                            # For single-word aliases, check substring matching
                            if len(word) >= 5 and len(alias) >= 5:
                                if word in alias.lower() or alias.lower() in word:
                                    similarity = max(similarity, 0.85)
                        
                        # Very high threshold for fuzzy matches to reduce false positives
                        if similarity > best_similarity and similarity >= 0.9:  # Raised from 0.8 to 0.9
                            best_similarity = similarity
                            best_match = f"{word} → {alias}"
                            match_type = "fuzzy"
            
            # Record significant matches
            if best_similarity >= 0.9:  # Updated threshold to match fuzzy matching
                matches.append({
                    "type_id": type_id,
                    "type_name": type_name,
                    "similarity": best_similarity,
                    "matched_term": best_match,
                    "match_type": match_type
                })
        
        # Sort matches by similarity (highest first)
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Determine the best match(es) and confidence
        if not matches:
            return [], 0.0, {
                "extracted_entities": [],
                "matched_document_types": [],
                "reasoning": ["No document type terms detected in query"],
                "method": "alias_fuzzy_matching"
            }
        
        # Take the highest scoring match(es)
        best_match = matches[0]
        confidence = best_match["similarity"]
        
        # Only return if confidence meets threshold
        if confidence >= confidence_threshold:
            # Get the primary match
            primary_match = best_match
            inferred_ids = [primary_match["type_id"]]
            
            # For overlapping document types, include both 2002 Act and 2018 Act versions
            # This handles cases where documents might be stored with either Act's document type
            document_type_aliases = get_all_document_type_aliases()
            primary_name = primary_match["type_name"]
            
            # Find all document types with the same name (overlapping types)
            overlapping_ids = []
            for type_id, type_info in document_type_aliases.items():
                if (type_info["name"] == primary_name and 
                    type_id != primary_match["type_id"]):
                    overlapping_ids.append(type_id)
                    logging.info(f"Also including overlapping document type: {type_id} ({type_info['name']})")
            
            if overlapping_ids:
                inferred_ids.extend(overlapping_ids)
                overlapping_note = f"Including all {primary_name} document types (both 2002 Act and 2018 Act versions)"
            else:
                overlapping_note = None
            
            logging.info(f"Document type inference: '{primary_match['matched_term']}' → {primary_match['type_name']} "
                        f"(IDs: {inferred_ids}) with {confidence:.3f} confidence")
            
            reasoning = [
                f"Detected document type '{primary_match['matched_term']}' matching '{primary_match['type_name']}' "
                f"with {confidence:.3f} confidence using {primary_match['match_type']} matching"
            ]
            if overlapping_note:
                reasoning.append(overlapping_note)
            
            return inferred_ids, confidence, {
                "extracted_entities": [primary_match["matched_term"]],
                "matched_document_types": [primary_match],
                "reasoning": reasoning,
                "method": "alias_fuzzy_matching"
            }
        else:
            return [], confidence, {
                "extracted_entities": [m["matched_term"] for m in matches[:3]],  # Top 3
                "matched_document_types": matches[:3],
                "reasoning": [
                    f"Best match '{best_match['matched_term']}' → {best_match['type_name']} "
                    f"with {confidence:.3f} confidence below threshold {confidence_threshold}"
                ],
                "method": "alias_fuzzy_matching"
            }

    def clean_query_after_inference(self, query: str, inference_metadata: Dict[str, Any]) -> str:
        """Clean the query by removing identified document type references.
        
        Args:
            query (str): The original search query
            inference_metadata (Dict[str, Any]): Metadata from the inference process
            
        Returns:
            str: Cleaned query with document type references removed
        """
        cleaned_query = query
        
        # Remove matched document type terms
        matched_types = inference_metadata.get("matched_document_types", [])
        for match in matched_types:
            matched_term = match.get("matched_term", "")
            if matched_term:
                if " → " in matched_term:
                    # For fuzzy matches, get the original word that was found in the query
                    original_word = matched_term.split(" → ")[0]
                    term_to_remove = original_word
                else:
                    # For exact matches, remove the matched alias term
                    term_to_remove = matched_term
                
                # Remove the term using word boundary matching (case insensitive)
                pattern = r'\b' + re.escape(term_to_remove) + r'\b'
                cleaned_query = re.sub(pattern, '', cleaned_query, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        cleaned_query = ' '.join(cleaned_query.split())
        
        logging.debug(f"Query cleaning: '{query}' → '{cleaned_query}'")
        return cleaned_query


# Create a singleton instance for easy importing
document_type_inference_service = DocumentTypeInferenceService()