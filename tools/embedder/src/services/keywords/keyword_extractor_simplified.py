# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
Simplified TF-IDF Implementation - Ultra-Fast

This implementation provides ultra-fast keyword extraction using enhanced TF-IDF
vectorization with domain-specific filtering.

Features:
- Enhanced TF-IDF vectorization with domain-specific filtering
- Processing time: ~2 seconds for 31 documents (948 chunks)
- Quality: High relevance with multi-word phrases and domain terms
- Best for: Retrospective updates, bulk processing, production workloads

Performance: Ultra-fast, recommended for bulk processing
"""

import time
from sklearn.feature_extraction.text import TfidfVectorizer

def extract_keywords_from_chunks_simplified(chunk_dicts, document_id=None):
    """
    Ultra-fast TF-IDF keyword extraction with domain-specific filtering.
    
    Args:
        chunk_dicts (list): List of chunk dictionaries with 'content' and 'metadata' fields
        document_id (str, optional): Identifier for the document being processed (for logging)
        
    Returns:
        tuple: (updated_chunk_dicts_with_keywords, set_of_all_unique_keywords)
    """
    import os
    start_time = time.time()
    
    # Create a short document identifier for logging
    doc_log_id = "unknown"
    if document_id:
        doc_log_id = os.path.basename(document_id)
        if len(doc_log_id) > 30:
            doc_log_id = doc_log_id[:27] + "..."
    
    texts = [chunk['content'] for chunk in chunk_dicts]
    if not texts:
        return chunk_dicts, set()
    
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}] Processing {len(texts)} chunks")
    
    return _extract_keywords_simplified(chunk_dicts, texts, start_time, doc_log_id)

def _extract_keywords_simplified(chunk_dicts, texts, start_time, doc_log_id):
    """Enhanced TF-IDF keyword extraction with improved quality"""
    extraction_start = time.time()
    
    # Domain-specific stopwords for environmental assessments
    domain_stopwords = {
        'project', 'projects', 'document', 'documents', 'assessment', 'report', 
        'section', 'sections', 'page', 'pages', 'table', 'figure', 'appendix',
        'chapter', 'part', 'item', 'items', 'will', 'may', 'shall', 'would',
        'could', 'should', 'must', 'can', 'also', 'however', 'therefore',
        'furthermore', 'additionally', 'respectively', 'including', 'such',
        'etc', 'eg', 'ie', 'see', 'refer', 'shown', 'described', 'noted'
    }
    
    # Handle single chunk documents - adjust TF-IDF parameters
    if len(texts) == 1:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),                # Keep 1-3 word phrases
            max_features=500,                  # Smaller vocabulary for single chunk
            stop_words='english',              # Built-in English stopwords
            min_df=1,                         # Minimum document frequency
            max_df=1.0,                       # Allow all terms for single document
            token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b',  # Better tokenization
            sublinear_tf=True,                # Sublinear TF scaling
            smooth_idf=False                  # No IDF smoothing for single doc
        )
    else:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),                # Keep 1-3 word phrases
            max_features=2000,                 # Increased vocabulary size
            stop_words='english',              # Built-in English stopwords
            min_df=1,                         # Minimum document frequency
            max_df=0.7,                       # Maximum document frequency (reduced)
            token_pattern=r'\b[a-zA-Z][a-zA-Z0-9]*\b',  # Better tokenization
            sublinear_tf=True,                # Sublinear TF scaling
            smooth_idf=True                   # Smooth IDF weights
        )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        all_keywords = set()
        for i, chunk in enumerate(chunk_dicts):
            # Get TF-IDF scores for this chunk
            chunk_scores = tfidf_matrix[i].toarray()[0]
            
            # Get terms above a minimum threshold
            min_score = 0.1  # Minimum TF-IDF score threshold
            scored_terms = [(feature_names[idx], chunk_scores[idx]) 
                          for idx in range(len(chunk_scores)) 
                          if chunk_scores[idx] > min_score]
            
            # Sort by score and filter
            scored_terms.sort(key=lambda x: x[1], reverse=True)
            
            keywords = []
            for term, score in scored_terms[:8]:  # Take top 8 candidates
                # Enhanced filtering
                if (len(term) > 2 and 
                    term.lower() not in domain_stopwords and
                    not term.isdigit() and
                    len(term) < 50 and  # Skip very long terms
                    score > min_score):
                    keywords.append(term)
                    
                if len(keywords) >= 5:  # Limit to 5 keywords per chunk
                    break
            
            chunk['metadata']['keywords'] = keywords
            all_keywords.update(keywords)
            
    except Exception as e:
        print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}] Enhanced TF-IDF extraction failed: {e}, falling back to empty keywords")
        for chunk in chunk_dicts:
            chunk['metadata']['keywords'] = []
        all_keywords = set()
    
    extraction_time = time.time() - extraction_start
    total_time = time.time() - start_time
    
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}] ENHANCED TF-IDF MODE TIMING:")
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}]   Enhanced TF-IDF extraction: {extraction_time:.3f}s")
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}]   Average per chunk: {extraction_time/len(texts):.3f}s")
    print(f"[KEYWORDS-SIMPLIFIED] [{doc_log_id}]   Extracted {len(all_keywords)} unique keywords")
    
    return chunk_dicts, all_keywords
