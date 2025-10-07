"""Helper functions for query enhancement and location relevance detection.

This module provides utilities for determining when to enhance search queries
with user location data based on the semantic content of the query.
"""

import re
from typing import Dict, Any, Tuple


def is_query_location_relevant(query: str, threshold: float = 0.7) -> Tuple[bool, float, Dict[str, Any]]:
    """Determine if a search query is semantically relevant to user location.
    
    Analyzes the query text to identify location-related intent patterns that would
    benefit from user location enhancement. Uses keyword matching and pattern analysis
    to calculate a relevance score.
    
    Args:
        query (str): The search query text to analyze
        threshold (float): Minimum score required to consider query location-relevant (default: 0.7)
        
    Returns:
        tuple: (is_relevant, score, metadata)
            - is_relevant (bool): True if query should be enhanced with user location
            - score (float): Relevance score from 0.0 to 1.0
            - metadata (dict): Details about the analysis including matched patterns
            
    Examples:
        >>> is_query_location_relevant("projects near me")
        (True, 0.9, {...})
        
        >>> is_query_location_relevant("environmental assessment report")
        (False, 0.1, {...})
    """
    query_lower = query.lower()
    
    # Define location-relevant patterns with different weights
    # High relevance patterns (0.9-1.0) - Strong location intent
    high_relevance_patterns = [
        (r'\bnear(by)?\s+(me|here|my location|where i am)\b', 1.0, 'near_me'),
        (r'\b(close|closest|nearest)\s+to\s+(me|here|my location)\b', 0.95, 'closest_to_me'),
        (r'\bin my (area|region|vicinity|neighborhood|city|town)\b', 0.9, 'in_my_area'),
        (r'\bwhere i (live|am|reside)\b', 0.9, 'where_i_live'),
        (r'\baround (me|here)\b', 0.9, 'around_me'),
    ]
    
    # Medium relevance patterns (0.6-0.8) - Moderate location intent
    medium_relevance_patterns = [
        (r'\bnear\s+\w+', 0.7, 'near_general'),  # "near something" (less specific)
        (r'\b(local|nearby|surrounding|proximate)\b', 0.7, 'proximity_terms'),
        (r'\b(distance|proximity|how far)\b', 0.7, 'distance_terms'),
        (r'\bwithin\s+\d+\s*(km|kilometers|miles|mi)\b', 0.8, 'distance_radius'),
        (r'\b(closest|nearest)\b', 0.6, 'proximity_superlatives'),
    ]
    
    # Low relevance patterns (0.3-0.5) - Weak location signals
    low_relevance_patterns = [
        (r'\b(location|locations|geographic|geographical)\b', 0.4, 'location_keywords'),
        (r'\b(regional|local area)\b', 0.5, 'regional_terms'),
    ]
    
    # Patterns that indicate NO location relevance (reduce score)
    non_location_patterns = [
        (r'\b(document|report|study|analysis|assessment)\s+(type|format|structure)\b', -0.3, 'document_structure'),
        (r'\b(who|what|when|why|how)\s+(is|are|was|were)\b', -0.2, 'information_questions'),
        (r'\b(definition|meaning|explain|describe)\b', -0.2, 'definitional_queries'),
    ]
    
    score = 0.0
    matched_patterns = []
    max_pattern_score = 0.0
    
    # Check high relevance patterns
    for pattern, weight, label in high_relevance_patterns:
        if re.search(pattern, query_lower):
            score = max(score, weight)  # Take highest score
            max_pattern_score = max(max_pattern_score, weight)
            matched_patterns.append({
                'pattern': label,
                'weight': weight,
                'category': 'high_relevance'
            })
    
    # Check medium relevance patterns if no high relevance found
    if score < 0.9:
        for pattern, weight, label in medium_relevance_patterns:
            if re.search(pattern, query_lower):
                score = max(score, weight)
                max_pattern_score = max(max_pattern_score, weight)
                matched_patterns.append({
                    'pattern': label,
                    'weight': weight,
                    'category': 'medium_relevance'
                })
    
    # Check low relevance patterns if no higher relevance found
    if score < 0.6:
        for pattern, weight, label in low_relevance_patterns:
            if re.search(pattern, query_lower):
                score = max(score, weight)
                max_pattern_score = max(max_pattern_score, weight)
                matched_patterns.append({
                    'pattern': label,
                    'weight': weight,
                    'category': 'low_relevance'
                })
    
    # Apply negative patterns (reduce score)
    for pattern, weight, label in non_location_patterns:
        if re.search(pattern, query_lower):
            score = max(0.0, score + weight)  # Apply penalty but don't go below 0
            matched_patterns.append({
                'pattern': label,
                'weight': weight,
                'category': 'negative'
            })
    
    # Determine if query is location-relevant based on threshold
    is_relevant = score > threshold
    
    # Build metadata
    metadata = {
        'score': round(score, 3),
        'threshold': threshold,
        'matched_patterns': matched_patterns,
        'pattern_count': len([p for p in matched_patterns if p['category'] != 'negative']),
        'max_pattern_score': round(max_pattern_score, 3),
        'query_length': len(query),
        'reasoning': _build_reasoning(is_relevant, score, matched_patterns, threshold)
    }
    
    return is_relevant, score, metadata


def _build_reasoning(is_relevant: bool, score: float, matched_patterns: list, threshold: float) -> str:
    """Build human-readable reasoning for the location relevance decision.
    
    Args:
        is_relevant (bool): Whether the query is considered location-relevant
        score (float): The calculated relevance score
        matched_patterns (list): List of matched pattern dictionaries
        threshold (float): The threshold used for the decision
        
    Returns:
        str: Human-readable explanation of the decision
    """
    if not matched_patterns:
        return f"No location-relevant patterns detected. Score {score:.2f} below threshold {threshold:.2f}."
    
    positive_patterns = [p for p in matched_patterns if p['category'] != 'negative']
    negative_patterns = [p for p in matched_patterns if p['category'] == 'negative']
    
    if is_relevant:
        pattern_desc = ", ".join([p['pattern'] for p in positive_patterns[:3]])
        return (f"Query is location-relevant (score: {score:.2f} >= {threshold:.2f}). "
                f"Detected patterns: {pattern_desc}. "
                f"User location will enhance search relevance.")
    else:
        if positive_patterns:
            pattern_desc = ", ".join([p['pattern'] for p in positive_patterns[:2]])
            return (f"Query has weak location signals (score: {score:.2f} < {threshold:.2f}). "
                    f"Patterns: {pattern_desc}. "
                    f"Not strong enough to warrant location enhancement.")
        else:
            return (f"Query is not location-relevant (score: {score:.2f}). "
                    f"No significant location-intent patterns detected.")


def format_user_location_for_query(user_location: Dict[str, Any]) -> str:
    """Format user location data into a human-readable string for query enhancement.
    
    Creates a natural language representation of user location data that can be
    appended to search queries for semantic matching.
    
    Args:
        user_location (dict): User location data with optional fields:
            - city (str): City name
            - region (str): Region/province/state
            - country (str): Country name
            - latitude (float): Latitude coordinate
            - longitude (float): Longitude coordinate
            
    Returns:
        str: Formatted location string (e.g., "Victoria, British Columbia, Canada")
        
    Examples:
        >>> format_user_location_for_query({"city": "Victoria", "region": "BC"})
        "Victoria, BC"
        
        >>> format_user_location_for_query({"latitude": 48.4284, "longitude": -123.3656})
        "coordinates: 48.4284, -123.3656"
    """
    if not user_location:
        return ""
    
    location_parts = []
    
    # Priority order: city, region, country
    if user_location.get('city'):
        location_parts.append(user_location['city'])
    
    if user_location.get('region'):
        location_parts.append(user_location['region'])
    
    if user_location.get('country'):
        location_parts.append(user_location['country'])
    
    # If we have city/region/country, return formatted string
    if location_parts:
        return ", ".join(location_parts)
    
    # Fallback to coordinates if available
    if user_location.get('latitude') is not None and user_location.get('longitude') is not None:
        lat = user_location['latitude']
        lon = user_location['longitude']
        return f"coordinates: {lat:.4f}, {lon:.4f}"
    
    return ""
