# Standard Query Keywords Extractor
# This module provides high-quality keyword extraction using KeyBERT
# with optimal settings for balanced performance and accuracy.

from flask import current_app
import logging

# Global model instance - loaded only once
_keymodel = None

def getKeywords(query, top_n=10):
    """
    Extract keywords using KeyBERT with standard settings.
    
    This provides high-quality semantic keyword extraction with balanced
    performance and accuracy using KeyBERT with MMR and diversity settings.
    
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
            
            logging.info(f"Initialized KeyBERT with model: {model_name}")
        except Exception as e:
            logging.error(f"Error initializing KeyBERT model: {str(e)}")
            return []

    try:
        keywords = _keymodel.extract_keywords(
            query,
            keyphrase_ngram_range=(1, 3),  # 1-3 word phrases
            use_mmr=True,  # Use Maximal Marginal Relevance for diversity
            diversity=0.8,  # Increased diversity for better coverage (matches embedder)
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
        logging.error(f"Error extracting keywords with standard method: {str(e)}")
        raise
