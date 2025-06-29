# Global model instance - loaded only once
from flask import current_app
import logging

_keymodel = None

def get_keywords(text):
    global _keymodel

    # Initialize the model only on first call
    if _keymodel is None:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer

        # Use strongly typed configuration instead of environment variables
        model_name = current_app.model_settings.keyword_model_name
        sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=sentence_model)

    try:
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            use_mmr=True,
            diversity=1,
            top_n=10,  # Limit to top 10 keywords for speed
        )
        words_to_remove = ["project", "projects"]
        filtered_keywords = [
            (word, score) for (word, score) in keywords if word not in words_to_remove
        ]
        return filtered_keywords
    except Exception as e:
        logging.error(f"Error extracting keywords: {str(e)}")
        # Return empty list as fallback
        return []


def match_keywords_to_documents(query_keywords, document_keywords_list, threshold=0.5):
    """
    Match query keywords against document-level keywords to find relevant documents.
    
    This function compares extracted query keywords with pre-stored document keywords
    to identify which documents are most likely to contain relevant information.
    
    Args:
        query_keywords (list): List of (keyword, score) tuples from query analysis
        document_keywords_list (list): List of document keyword sets from database
        threshold (float): Minimum keyword score threshold for matching (default: 0.5)
        
    Returns:
        list: List of document indices sorted by keyword match relevance
    """
    if not query_keywords or not document_keywords_list:
        return []
        
    try:
        query_words = [word.lower() for word, score in query_keywords if score >= threshold]
        if not query_words:
            return []
            
        document_scores = []
        
        for doc_idx, doc_keywords in enumerate(document_keywords_list):
            if not doc_keywords:
                document_scores.append((doc_idx, 0.0))
                continue
                
            # Handle both list and dict formats for document keywords
            if isinstance(doc_keywords, dict):
                doc_words = [word.lower() for word in doc_keywords.keys()]
            elif isinstance(doc_keywords, list):
                doc_words = [word.lower() for word in doc_keywords]
            else:
                document_scores.append((doc_idx, 0.0))
                continue
                
            # Calculate overlap score
            overlap_count = len(set(query_words) & set(doc_words))
            overlap_score = overlap_count / len(query_words) if query_words else 0.0
            
            document_scores.append((doc_idx, overlap_score))
        
        # Sort by score descending and return document indices
        document_scores.sort(key=lambda x: x[1], reverse=True)
        return [doc_idx for doc_idx, score in document_scores if score > 0]
        
    except Exception as e:
        logging.error(f"Error matching keywords to documents: {str(e)}")
        return []


def extract_keywords_for_document_search(text, top_n=5):
    """
    Extract keywords specifically optimized for document-level matching.
    
    This function extracts a smaller set of high-quality keywords that are
    more suitable for matching against pre-computed document keywords.
    
    Args:
        text (str): The query text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 5)
        
    Returns:
        list: List of (keyword, score) tuples, limited to top_n results
    """
    try:
        all_keywords = get_keywords(text)
        # Return only the top N keywords for document matching
        return all_keywords[:top_n]
    except Exception as e:
        logging.error(f"Error extracting keywords for document search: {str(e)}")
        return []
