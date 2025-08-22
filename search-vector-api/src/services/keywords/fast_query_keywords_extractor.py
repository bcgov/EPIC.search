# Fast Query Keywords Extractor
# This module provides fast keyword extraction using KeyBERT
# with lightweight settings for good performance.

from flask import current_app
import logging

# Global KeyBERT model instance - loaded only once
_keymodel = None


def getKeywords(query, top_n=10):
    """
    Extract keywords using KeyBERT with fast/lightweight settings.
    
    This method uses KeyBERT with optimized settings for speed while
    maintaining reasonable quality. Uses lower diversity for faster processing.
    
    Args:
        query (str): The query text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 10)
        
    Returns:
        list: List of (keyword, score) tuples from KeyBERT
    """
    global _keymodel

    # Initialize the model only on first call
    if _keymodel is None:
        try:
            from keybert import KeyBERT
            from sentence_transformers import SentenceTransformer

            # Use strongly typed configuration instead of environment variables
            model_name = current_app.model_settings.keyword_model_name
            sentence_model = SentenceTransformer(model_name)
            _keymodel = KeyBERT(model=sentence_model)
            
            logging.info(f"Initialized KeyBERT (fast mode) with model: {model_name}")
        except Exception as e:
            logging.error(f"Error initializing KeyBERT model for fast mode: {str(e)}")
            return []

    try:
        keywords = _keymodel.extract_keywords(
            query,
            keyphrase_ngram_range=(1, 2),  # Shorter phrases for speed (1-2 words vs 1-3)
            use_mmr=False,  # Disabled MMR for major speed boost (matches embedder)
            top_n=top_n,  # Limit to requested number of keywords
        )
        
        # Domain-specific stopwords for environmental assessments (matches embedder)
        words_to_remove = {
            'project', 'projects', 'document', 'documents', 'assessment', 'report', 
            'section', 'sections', 'page', 'pages', 'table', 'figure', 'appendix',
            'chapter', 'part', 'item', 'items', 'will', 'may', 'shall', 'would',
            'could', 'should', 'must', 'can', 'also', 'however', 'therefore',
            'furthermore', 'additionally', 'respectively', 'including', 'such',
            'etc', 'eg', 'ie', 'see', 'refer', 'shown', 'described', 'noted',
            'within', 'during', 'following', 'according', 'regarding', 'concerning'
        }
        
        filtered_keywords = [
            (word, score) for (word, score) in keywords 
            if word.lower() not in words_to_remove and len(word) > 2 and len(word) < 50 and not word.isdigit()
        ]
        
        return filtered_keywords
    except Exception as e:
        logging.error(f"Error extracting keywords with fast KeyBERT method: {str(e)}")
        raise
