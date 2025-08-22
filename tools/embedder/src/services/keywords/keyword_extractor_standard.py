# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

import time
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

"""
Standard KeyBERT Implementation - Highest Quality

This implementation provides the highest quality keyword extraction using
full KeyBERT with MMR (Maximal Marginal Relevance) and comprehensive n-gram ranges.

Features:
- KeyBERT with full n-gram range (1,3), MMR enabled for diversity
- Parallelized per-chunk extraction with ThreadPoolExecutor  
- Enhanced domain-specific stopword filtering
- Semantic similarity deduplication for reduced redundancy
- Quality-focused score thresholding and filtering
- Detailed timing and performance logging
- Highest semantic quality with comprehensive keyword diversity

Performance: Baseline (slowest but highest quality)
"""

_keymodel = None
_sentence_model = None

def extract_keywords_from_chunks_standard(chunk_dicts, document_id=None):
    """
    Parallelized keyword extraction for a list of chunk dicts using standard KeyBERT.
    Adds a 'keywords' field to each chunk dict's metadata and returns the updated list and all unique keywords.
    Uses ThreadPoolExecutor for speed and robust per-chunk extraction.
    
    Extraction is optimized for high-impact keywords:
    - top_n=5 to reduce keyword volume while maintaining relevance (vs 10+ which creates noise)
    - diversity=0.7 for focused keywords rather than maximally diverse ones
    - For large documents (500+ pages), this prevents keyword explosion (20k+ → 10k keywords)
    - Improves signal-to-noise ratio and makes analytics more manageable
    
    Args:
        chunk_dicts (list): List of chunk dictionaries with 'content' and 'metadata' fields
        document_id (str, optional): Identifier for the document being processed (for logging)
        
    Returns:
        tuple: (updated_chunk_dicts_with_keywords, set_of_all_unique_keywords)
    """
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
        print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Loading models...")
        model_name = settings.keyword_extraction_settings.model_name
        _sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=_sentence_model)
        model_load_time = time.time() - model_load_start
        print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Model loading took {model_load_time:.2f}s")
    else:
        model_load_time = 0
        print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Using cached models")
    
    # Time text preparation
    prep_start = time.time()
    texts = [chunk['content'] for chunk in chunk_dicts]
    if not texts:
        return chunk_dicts, set()
    prep_time = time.time() - prep_start
    
    all_keywords = set()
    chunk_count = len(texts)
    max_workers = min(settings.multi_processing_settings.keyword_extraction_workers, chunk_count)
    
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Processing {chunk_count} chunks with {max_workers} threads (full KeyBERT)")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Text preparation took {prep_time:.3f}s")
    
    def extract_for_text(text):
        """Extract keywords for a single text chunk with detailed timing and enhanced quality filtering"""
        chunk_start = time.time()
        
        # Domain-specific stopwords for environmental assessments
        domain_stopwords = {
            'project', 'projects', 'document', 'documents', 'assessment', 'report', 
            'section', 'sections', 'page', 'pages', 'table', 'figure', 'appendix',
            'chapter', 'part', 'item', 'items', 'will', 'may', 'shall', 'would',
            'could', 'should', 'must', 'can', 'also', 'however', 'therefore',
            'furthermore', 'additionally', 'respectively', 'including', 'such',
            'etc', 'eg', 'ie', 'see', 'refer', 'shown', 'described', 'noted',
            'within', 'during', 'following', 'according', 'regarding', 'concerning'
        }
        
        # Time the actual KeyBERT extraction - ENHANCED PARAMETERS FOR QUALITY
        extract_start = time.time()
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),  # FULL n-gram range for maximum coverage
            use_mmr=True,                  # MMR enabled for keyword diversity
            diversity=0.8,                 # INCREASED diversity for better coverage (0.7 → 0.8)
            top_n=8                        # INCREASED from 5 to 8 for better quality filtering
        )
        extract_time = time.time() - extract_start
        
        # Time the enhanced filtering with quality focus
        filter_start = time.time()
        
        # Score threshold for quality (only keep high-confidence keywords)
        min_score = 0.15  # Higher threshold for standard mode quality
        
        filtered_keywords = []
        for word, score in keywords:
            # Enhanced quality filtering
            if (score >= min_score and  # Score threshold
                word.lower() not in domain_stopwords and  # Domain filtering
                len(word) > 2 and  # Minimum length
                len(word) < 50 and  # Maximum length (avoid long artifacts)
                not word.isdigit() and  # No pure numbers
                not word.replace(' ', '').isdigit() and  # No spaced numbers
                len(word.split()) <= 3 and  # Maximum 3 words per phrase
                word.count(' ') <= 2):  # Alternative check for phrase length
                
                # Additional quality checks
                if not word.lower().startswith(('www', 'http', 'https', 'ftp')):  # No URLs
                    filtered_keywords.append(word)
                    
                # Limit to top 5 highest-quality keywords per chunk
                if len(filtered_keywords) >= 5:
                    break
        
        filter_time = time.time() - filter_start
        chunk_total_time = time.time() - chunk_start
        
        # Log timing for slow chunks
        if chunk_total_time > 1.0:  # Log slow chunks
            print(f"[KEYWORDS-STANDARD] [{doc_log_id}] SLOW CHUNK: {chunk_total_time:.3f}s total (extract: {extract_time:.3f}s, filter: {filter_time:.3f}s) - text length: {len(text)}")
        
        return filtered_keywords
    
    # Time the parallel execution
    execution_start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        keywords_results = list(executor.map(extract_for_text, texts))
    execution_time = time.time() - execution_start
    
    # Time the result aggregation with enhanced document-level quality filtering
    aggregation_start = time.time()
    
    # First pass: collect all keywords and track frequency
    keyword_frequency = defaultdict(int)
    all_chunk_keywords = []
    
    for i, chunk in enumerate(chunk_dicts):
        filtered_keywords = keywords_results[i]
        chunk['metadata']['keywords'] = filtered_keywords
        all_chunk_keywords.extend(filtered_keywords)
        
        # Track frequency for each keyword across chunks
        for keyword in filtered_keywords:
            keyword_frequency[keyword] += 1
    
    # Enhanced document-level keyword consolidation with semantic similarity filtering
    unique_keywords = list(set(all_chunk_keywords))
    final_keywords = set()
    
    if unique_keywords:
        try:
            # Use semantic similarity to reduce redundancy for high-quality results
            # Get embeddings for all unique keywords using the same model
            keyword_embeddings = _sentence_model.encode(unique_keywords)
            
            # Calculate similarity matrix
            similarity_matrix = cosine_similarity(keyword_embeddings)
            
            # Select keywords with diversity and frequency weighting
            selected_indices = set()
            
            # Sort keywords by frequency (higher frequency = higher priority)
            keywords_with_freq = [(kw, keyword_frequency[kw]) for kw in unique_keywords]
            keywords_with_freq.sort(key=lambda x: x[1], reverse=True)
            
            for i, (keyword, freq) in enumerate(keywords_with_freq):
                original_idx = unique_keywords.index(keyword)
                
                # Check if this keyword is too similar to already selected ones
                too_similar = False
                for selected_idx in selected_indices:
                    if similarity_matrix[original_idx][selected_idx] > 0.85:  # High similarity threshold
                        too_similar = True
                        break
                
                if not too_similar:
                    selected_indices.add(original_idx)
                    final_keywords.add(keyword)
                    
                    # Limit to top 15 highest-quality, diverse keywords for standard mode
                    if len(final_keywords) >= 15:
                        break
                        
            print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Semantic deduplication: {len(unique_keywords)} → {len(final_keywords)} keywords")
                        
        except Exception as e:
            # Fallback to frequency-based selection if similarity check fails
            print(f"[KEYWORDS-STANDARD] [{doc_log_id}] Similarity filtering failed, using frequency fallback: {e}")
            
            # Sort by frequency and take top unique keywords
            keywords_with_freq = [(kw, keyword_frequency[kw]) for kw in unique_keywords]
            keywords_with_freq.sort(key=lambda x: x[1], reverse=True)
            final_keywords = set([kw for kw, freq in keywords_with_freq[:15]])
    
    aggregation_time = time.time() - aggregation_start
    
    total_time = time.time() - start_time
    avg_time_per_chunk = execution_time / chunk_count if chunk_count > 0 else 0
    
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}] FULL KEYBERT MODE TIMING:")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Model loading: {model_load_time:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Text prep: {prep_time:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Parallel execution: {execution_time:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Result aggregation: {aggregation_time:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Average per chunk: {avg_time_per_chunk:.3f}s")
    print(f"[KEYWORDS-STANDARD] [{doc_log_id}]   Extracted {len(final_keywords)} unique keywords (enhanced quality)")
    
    return chunk_dicts, final_keywords

# Export the function with the expected name for the factory
extract_keywords = extract_keywords_from_chunks_standard
