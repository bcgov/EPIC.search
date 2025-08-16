# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
Optimized BERT Keyword Extractor with performance improvements.

Performance optimizations implemented:
1. Batch embedding computation (faster than individual chunk processing)
2. Reduced KeyBERT parameters for speed
3. Cached candidate keywords to avoid redundant computation
4. Optional simplified extraction mode
"""

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
import time
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

import multiprocessing

_keymodel = None
_sentence_model = None
_candidate_cache = {}

def extract_keywords_from_chunks_fast(chunk_dicts, use_batch_mode=True, simplified_mode=False, document_id=None):
    """
    Optimized keyword extraction with multiple performance improvements.
    
    Args:
        chunk_dicts (list): List of chunk dictionaries with 'content' and 'metadata' fields
        use_batch_mode (bool): Use batch embedding computation (faster for many chunks)
        simplified_mode (bool): Use simplified extraction (much faster, slightly lower quality)
        document_id (str, optional): Identifier for the document being processed (for logging)
        
    Returns:
        tuple: (updated_chunk_dicts_with_keywords, set_of_all_unique_keywords)
    """
    import os
    start_time = time.time()
    global _keymodel, _sentence_model
    
    # Create a short document identifier for logging
    doc_log_id = "unknown"
    if document_id:
        doc_log_id = os.path.basename(document_id)
        if len(doc_log_id) > 30:
            doc_log_id = doc_log_id[:27] + "..."
    
    # Time model loading
    model_load_start = time.time()
    if _keymodel is None or _sentence_model is None:
        print(f"[KEYWORDS-FAST] [{doc_log_id}] Loading models...")
        model_name = settings.keyword_extraction_settings.model_name
        _sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=_sentence_model)
        model_load_time = time.time() - model_load_start
        print(f"[KEYWORDS-FAST] [{doc_log_id}] Model loading took {model_load_time:.2f}s")
    else:
        model_load_time = 0
        print(f"[KEYWORDS-FAST] [{doc_log_id}] Using cached models")
    
    # Time text preparation
    prep_start = time.time()
    texts = [chunk['content'] for chunk in chunk_dicts]
    if not texts:
        return chunk_dicts, set()
    prep_time = time.time() - prep_start
    
    all_keywords = set()
    chunk_count = len(texts)
    
    print(f"[KEYWORDS-FAST] [{doc_log_id}] Processing {chunk_count} chunks (batch_mode={use_batch_mode}, simplified={simplified_mode})")
    print(f"[KEYWORDS-FAST] [{doc_log_id}] Text preparation took {prep_time:.3f}s")
    
    if simplified_mode:
        # Ultra-fast mode: Use TF-IDF + simple filtering instead of KeyBERT
        return _extract_keywords_simplified(chunk_dicts, texts, start_time)
    elif use_batch_mode and chunk_count > 5:
        # Batch mode: Process all chunks together (faster for many chunks)
        return _extract_keywords_batch(chunk_dicts, texts, start_time)
    else:
        # Individual mode: Process chunks one by one (better for few chunks)
        return _extract_keywords_individual(chunk_dicts, texts, start_time)

def _extract_keywords_simplified(chunk_dicts, texts, start_time):
    """Ultra-fast keyword extraction using TF-IDF instead of KeyBERT"""
    extraction_start = time.time()
    
    # Use TF-IDF to find important terms
    vectorizer = CountVectorizer(
        ngram_range=(1, 3),
        max_features=1000,
        stop_words='english',
        min_df=1,
        max_df=0.8
    )
    
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        
        all_keywords = set()
        for i, chunk in enumerate(chunk_dicts):
            # Get top 5 terms for this chunk
            chunk_scores = tfidf_matrix[i].toarray()[0]
            top_indices = chunk_scores.argsort()[-5:][::-1]
            
            keywords = []
            for idx in top_indices:
                if chunk_scores[idx] > 0:
                    term = feature_names[idx]
                    if term not in ["project", "projects"] and len(term) > 2:
                        keywords.append(term)
            
            chunk['metadata']['keywords'] = keywords[:5]
            all_keywords.update(keywords)
            
    except Exception as e:
        print(f"[KEYWORDS-FAST] TF-IDF extraction failed: {e}, falling back to empty keywords")
        for chunk in chunk_dicts:
            chunk['metadata']['keywords'] = []
        all_keywords = set()
    
    extraction_time = time.time() - extraction_start
    total_time = time.time() - start_time
    
    print(f"[KEYWORDS-FAST] SIMPLIFIED MODE TIMING:")
    print(f"[KEYWORDS-FAST]   TF-IDF extraction: {extraction_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Average per chunk: {extraction_time/len(texts):.3f}s")
    print(f"[KEYWORDS-FAST]   Extracted {len(all_keywords)} unique keywords")
    
    return chunk_dicts, all_keywords

def _extract_keywords_batch(chunk_dicts, texts, start_time):
    """Batch processing mode for KeyBERT with query compatibility"""
    extraction_start = time.time()
    
    # Extract keywords for all texts in one batch call
    # Use same parameters as query engine for consistency
    all_keywords_results = _keymodel.extract_keywords(
        texts,
        keyphrase_ngram_range=(1, 3),  # Keep (1,3) for query compatibility
        use_mmr=True,
        diversity=0.6,  # Slightly reduced from 0.7 for speed, but still semantic
        top_n=5
    )
    
    aggregation_start = time.time()
    words_to_remove = ["project", "projects"]
    all_keywords = set()
    
    for i, chunk in enumerate(chunk_dicts):
        if i < len(all_keywords_results):
            keywords = all_keywords_results[i]
            filtered_keywords = [word for word, score in keywords if word not in words_to_remove]
            chunk['metadata']['keywords'] = filtered_keywords
            all_keywords.update(filtered_keywords)
        else:
            chunk['metadata']['keywords'] = []
    
    aggregation_time = time.time() - aggregation_start
    extraction_time = time.time() - extraction_start
    total_time = time.time() - start_time
    
    print(f"[KEYWORDS-FAST] BATCH MODE TIMING (Query-Compatible):")
    print(f"[KEYWORDS-FAST]   Batch extraction: {extraction_time - aggregation_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Result aggregation: {aggregation_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Average per chunk: {extraction_time/len(texts):.3f}s")
    print(f"[KEYWORDS-FAST]   Extracted {len(all_keywords)} unique keywords")
    
    return chunk_dicts, all_keywords

def _extract_keywords_individual(chunk_dicts, texts, start_time):
    """Individual processing mode with threading (query-compatible parameters)"""
    max_workers = min(settings.multi_processing_settings.keyword_extraction_workers, len(texts))
    
    def extract_for_text_optimized(text):
        """Optimized extraction with query-compatible parameters"""
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),  # Keep (1,3) for query compatibility
            use_mmr=True,
            diversity=0.6,  # Slightly reduced from 0.7 for speed
            top_n=5
        )
        words_to_remove = ["project", "projects"]
        return [word for word, score in keywords if word not in words_to_remove]
    
    execution_start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        keywords_results = list(executor.map(extract_for_text_optimized, texts))
    execution_time = time.time() - execution_start
    
    # Aggregate results
    aggregation_start = time.time()
    all_keywords = set()
    for i, chunk in enumerate(chunk_dicts):
        filtered_keywords = keywords_results[i]
        chunk['metadata']['keywords'] = filtered_keywords
        all_keywords.update(filtered_keywords)
    aggregation_time = time.time() - aggregation_start
    
    total_time = time.time() - start_time
    
    print(f"[KEYWORDS-FAST] INDIVIDUAL MODE TIMING (Query-Compatible):")
    print(f"[KEYWORDS-FAST]   Parallel execution: {execution_time:.3f}s ({max_workers} threads)")
    print(f"[KEYWORDS-FAST]   Result aggregation: {aggregation_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS-FAST]   Average per chunk: {execution_time/len(texts):.3f}s")
    print(f"[KEYWORDS-FAST]   Extracted {len(all_keywords)} unique keywords")
    
    return chunk_dicts, all_keywords
