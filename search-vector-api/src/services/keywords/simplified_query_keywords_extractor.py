# Simplified Query Keywords Extractor
# This module provides TF-IDF keyword extraction matching the embedder
# for maximum performance with statistical quality.

import logging

# Global TF-IDF vectorizer instance - loaded only once
_tfidf_vectorizer = None


def getKeywords(query, top_n=10):
    """
    Extract keywords using enhanced TF-IDF method matching the embedder implementation.
    
    This method uses the same TF-IDF configuration as the embedder's simplified mode
    to ensure query keywords match document keyword extraction.
    
    Args:
        query (str): The query text to extract keywords from
        top_n (int): Maximum number of keywords to return (default: 10)
        
    Returns:
        list: List of (keyword, score) tuples, sorted by TF-IDF score
    """
    global _tfidf_vectorizer
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        import re
        
        # Domain-specific stopwords for environmental assessments (matches embedder)
        domain_stopwords = {
            'project', 'projects', 'document', 'documents', 'assessment', 'report', 
            'section', 'sections', 'page', 'pages', 'table', 'figure', 'appendix',
            'chapter', 'part', 'item', 'items', 'will', 'may', 'shall', 'would',
            'could', 'should', 'must', 'can', 'also', 'however', 'therefore',
            'furthermore', 'additionally', 'respectively', 'including', 'such',
            'etc', 'eg', 'ie', 'see', 'refer', 'shown', 'described', 'noted',
            'within', 'during', 'following', 'according', 'regarding', 'concerning'
        }
        
        # Initialize the TF-IDF vectorizer to match embedder configuration
        if _tfidf_vectorizer is None:
            _tfidf_vectorizer = TfidfVectorizer(
                ngram_range=(1, 3),                # Keep 1-3 word phrases (matches embedder)
                max_features=2000,                 # Increased vocabulary size (matches embedder)
                stop_words='english',              # Built-in English stopwords
                min_df=1,                         # Minimum document frequency
                max_df=0.7,                       # Maximum document frequency (matches embedder)
                token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b',  # Better tokenization (matches embedder)
                sublinear_tf=True,                # Sublinear TF scaling (matches embedder)
                smooth_idf=True                   # Smooth IDF weights (matches embedder)
            )
            logging.info("Initialized enhanced TF-IDF vectorizer for simplified keyword extraction")
        
        # For single query, create a minimal corpus by splitting into meaningful segments
        # This approach better matches how the embedder processes document chunks
        sentences = re.split(r'[.!?;\n]+', query)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        # If we have meaningful sentences, use them; otherwise use word-based segments
        if len(sentences) >= 2:
            texts = sentences
        else:
            # Split into word groups to create artificial "documents" for TF-IDF
            words = query.split()
            if len(words) > 6:
                # Create overlapping segments
                segment_size = max(len(words) // 3, 3)
                texts = []
                for i in range(0, len(words), segment_size):
                    segment = ' '.join(words[i:i + segment_size * 2])  # Overlapping segments
                    if segment.strip():
                        texts.append(segment)
                if len(texts) < 2:
                    texts = [query, query]  # Fallback
            else:
                texts = [query, query]  # Simple fallback for very short queries
        
        # Fit TF-IDF on the text segments
        tfidf_matrix = _tfidf_vectorizer.fit_transform(texts)
        feature_names = _tfidf_vectorizer.get_feature_names_out()
        
        # Calculate average TF-IDF scores across all segments
        mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # Apply quality threshold (matches embedder)
        min_score = 0.1  # Minimum TF-IDF score threshold
        
        # Get scored terms above threshold
        scored_terms = [(feature_names[idx], mean_scores[idx]) 
                       for idx in range(len(mean_scores)) 
                       if mean_scores[idx] > min_score]
        
        # Sort by score
        scored_terms.sort(key=lambda x: x[1], reverse=True)
        
        # Apply enhanced filtering (matches embedder)
        keywords = []
        for term, score in scored_terms[:top_n * 2]:  # Get more candidates for filtering
            if (len(term) > 2 and 
                term.lower() not in domain_stopwords and
                not term.isdigit() and
                len(term) < 50 and  # Skip very long terms
                score > min_score):
                keywords.append((term, float(score)))
                
            if len(keywords) >= top_n:  # Limit to requested number
                break
        
        return keywords
        
    except Exception as e:
        logging.error(f"Error extracting enhanced TF-IDF keywords: {str(e)}")
        raise
