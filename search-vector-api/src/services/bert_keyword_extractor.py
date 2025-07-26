# Global model instances - loaded only once
from flask import current_app

import logging

_keymodel = None
_tfidf_vectorizer = None

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
    The extraction method used depends on the document keyword extraction method
    configured in the application settings.
    
    Args:
        text (str): The query text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 5)
        
    Returns:
        list: List of (keyword, score) tuples, limited to top_n results
    """
    try:
        # Check which extraction method was used for documents
        extraction_method = current_app.model_settings.document_keyword_extraction_method
        
        if extraction_method == "tfidf":
            return get_tfidf_keywords(text, top_n=top_n)
        else:  # default to keybert
            all_keywords = get_keywords(text)
            # Return only the top N keywords for document matching
            return all_keywords[:top_n]
    except Exception as e:
        logging.error(f"Error extracting keywords for document search: {str(e)}")
        return []


def get_tfidf_keywords(text, top_n=10):
    """
    Extract keywords using TF-IDF (Term Frequency-Inverse Document Frequency) method.
    
    This method uses statistical frequency-based keyword extraction instead of 
    semantic embeddings. It's suitable for matching against document keywords
    that were also extracted using TF-IDF methods.
    
    Args:
        text (str): The text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 10)
        
    Returns:
        list: List of (keyword, score) tuples, sorted by TF-IDF score
    """
    global _tfidf_vectorizer
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        import re
        
        # Initialize the TF-IDF vectorizer on first call
        if _tfidf_vectorizer is None:
            _tfidf_vectorizer = TfidfVectorizer(
                max_features=1000,  # Limit vocabulary size
                ngram_range=(1, 3),  # Use 1-3 word phrases like KeyBERT
                stop_words='english',  # Remove common English stop words
                lowercase=True,
                token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b',  # Only alphanumeric tokens starting with letter
                min_df=1,  # Minimum document frequency
                max_df=0.95  # Maximum document frequency (remove very common words)
            )
        
        # For a single query, we need to create a small corpus to calculate TF-IDF
        # We'll split the text into sentences to create multiple "documents"
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If we only have one sentence, duplicate it to allow TF-IDF calculation
        if len(sentences) <= 1:
            sentences = [text] * 2
        
        # Fit TF-IDF on the sentences
        tfidf_matrix = _tfidf_vectorizer.fit_transform(sentences)
        feature_names = _tfidf_vectorizer.get_feature_names_out()
        
        # Calculate average TF-IDF scores across all sentences
        mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # Get indices of top scoring terms
        top_indices = np.argsort(mean_scores)[::-1][:top_n]
        
        # Create list of (keyword, score) tuples
        keywords = []
        words_to_remove = {"project", "projects"}  # Same filtering as KeyBERT
        
        for idx in top_indices:
            keyword = feature_names[idx]
            score = mean_scores[idx]
            
            if keyword not in words_to_remove and score > 0:
                keywords.append((keyword, float(score)))
        
        return keywords[:top_n]
        
    except Exception as e:
        logging.error(f"Error extracting TF-IDF keywords: {str(e)}")
        # Fallback to simple word extraction if TF-IDF fails
        return extract_simple_keywords(text, top_n)


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
