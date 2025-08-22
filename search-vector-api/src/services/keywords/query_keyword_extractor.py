"""
Query Keyword Extractor - Main Interface

CRITICAL: This module's extraction method MUST match the embedder's keyword extraction
configuration exactly. Query keywords must be extracted using the same algorithm,
parameters, and filtering that was used when the documents were originally embedded.

Mismatched extraction methods will result in poor search relevance because query
keywords won't align with how document keywords were processed during embedding.
"""

from flask import current_app
from .simplified_query_keywords_extractor import getKeywords as simplified_extract
from .fast_query_keywords_extractor import getKeywords as fast_extract
from .standard_query_keywords_extractor import getKeywords as standard_extract

import logging

def get_keywords(text, top_n=10):
    """
    Extract keywords using the configured extraction method.
    
    This function delegates to the appropriate extraction method based on
    the DOCUMENT_KEYWORD_EXTRACTION_METHOD configuration setting.
    
    ⚠️ CRITICAL: The configured method must match your embedder's keyword extraction
    method exactly for optimal search results.
    
    Args:
        text (str): The text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 10)
        
    Returns:
        list: List of (keyword, score) tuples
    """
    try:
        # Get the configured extraction method
        extraction_method = current_app.model_settings.document_keyword_extraction_method
        
        if extraction_method == "simplified":
            return simplified_extract(text, top_n)
        elif extraction_method == "fast":
            return fast_extract(text, top_n)
        else:  # default to standard
            return standard_extract(text, top_n)
            
    except Exception as e:
        logging.error(f"Error extracting keywords: {str(e)}")
        # Fallback to simplified extraction
        try:
            return simplified_extract(text, top_n)
        except Exception as fallback_e:
            logging.error(f"Fallback extraction also failed: {str(fallback_e)}")
            return []
        

def extract_simple_keywords(text, top_n=10):
    """
    Simple fallback keyword extraction when advanced methods fail.
    
    Extracts important-looking words from text using basic heuristics.
    
    Args:
        text (str): The text to extract keywords from
        top_n (int): Maximum number of keywords to return
        
    Returns:
        list: List of (keyword, score) tuples with uniform scores
    """
    try:
        import re
        from collections import Counter
        
        # Basic text processing
        text = text.lower()
        # Extract words (alphanumeric, 3+ characters)
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', text)
        
        # Simple stop words to remove
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one',
            'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see',
            'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'that',
            'with', 'have', 'this', 'will', 'your', 'from', 'they', 'know', 'want', 'been', 'good',
            'much', 'some', 'time', 'very', 'when', 'come', 'here', 'just', 'like', 'long', 'make',
            'many', 'over', 'such', 'take', 'than', 'them', 'well', 'were', 'what', 'project', 'projects'
        }
        
        # Filter out stop words and count frequency
        filtered_words = [word for word in words if word not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Get most common words
        most_common = word_counts.most_common(top_n)
        
        # Convert to (keyword, score) format with normalized scores
        max_count = most_common[0][1] if most_common else 1
        keywords = [(word, count / max_count) for word, count in most_common]
        
        return keywords
        
    except Exception as e:
        logging.error(f"Error in simple keyword extraction: {str(e)}")
        return []
