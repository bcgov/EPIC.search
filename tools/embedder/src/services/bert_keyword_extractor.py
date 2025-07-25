# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
BERT Keyword Extractor module for extracting relevant keywords from text using KeyBERT and SentenceTransformer.

- Uses a dedicated keyword extraction model (configurable)
- Parallelizes per-chunk extraction for speed
- Handles lazy model loading for fast startup
- Compatible with all KeyBERT versions (no precomputed embedding batching)
"""

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor
import time

import multiprocessing

_keymodel = None
_sentence_model = None

def extract_keywords_from_chunks(chunk_dicts):
    """
    Parallelized keyword extraction for a list of chunk dicts.
    Adds a 'keywords' field to each chunk dict's metadata and returns the updated list and all unique keywords.
    Uses ThreadPoolExecutor for speed and robust per-chunk extraction.
    
    Extraction is optimized for high-impact keywords:
    - top_n=5 to reduce keyword volume while maintaining relevance (vs 10+ which creates noise)
    - diversity=0.7 for focused keywords rather than maximally diverse ones
    - For large documents (500+ pages), this prevents keyword explosion (20k+ → 10k keywords)
    - Improves signal-to-noise ratio and makes analytics more manageable
    
    Args:
        chunk_dicts (list): List of chunk dictionaries with 'content' and 'metadata' fields
        
    Returns:
        tuple: (updated_chunk_dicts_with_keywords, set_of_all_unique_keywords)
    """
    start_time = time.time()
    global _keymodel, _sentence_model
    
    # Time model loading
    model_load_start = time.time()
    if _keymodel is None or _sentence_model is None:
        print(f"[KEYWORDS] Loading models...")
        model_name = settings.keyword_extraction_settings.model_name
        _sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=_sentence_model)
        model_load_time = time.time() - model_load_start
        print(f"[KEYWORDS] Model loading took {model_load_time:.2f}s")
    else:
        model_load_time = 0
        print(f"[KEYWORDS] Using cached models")
    
    # Time text preparation
    prep_start = time.time()
    texts = [chunk['content'] for chunk in chunk_dicts]
    if not texts:
        return chunk_dicts, set()
    prep_time = time.time() - prep_start
    
    all_keywords = set()
    chunk_count = len(texts)
    max_workers = min(settings.multi_processing_settings.keyword_extraction_workers, chunk_count)
    
    print(f"[KEYWORDS] Processing {chunk_count} chunks with {max_workers} threads")
    print(f"[KEYWORDS] Text preparation took {prep_time:.3f}s")
    
    def extract_for_text(text):
        """Extract keywords for a single text chunk with detailed timing"""
        chunk_start = time.time()
        
        # Time the actual KeyBERT extraction
        extract_start = time.time()
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            use_mmr=True,
            diversity=0.7,
            top_n=5
        )
        extract_time = time.time() - extract_start
        
        # Time the filtering
        filter_start = time.time()
        words_to_remove = ["project", "projects"]
        filtered_keywords = [word for word, score in keywords if word not in words_to_remove]
        filter_time = time.time() - filter_start
        
        chunk_total_time = time.time() - chunk_start
        
        # Log timing for every 10th chunk or slow chunks
        if chunk_total_time > 1.0:  # Log slow chunks
            print(f"[KEYWORDS] SLOW CHUNK: {chunk_total_time:.3f}s total (extract: {extract_time:.3f}s, filter: {filter_time:.3f}s) - text length: {len(text)}")
        
        return filtered_keywords
    
    # Time the parallel execution
    execution_start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        keywords_results = list(executor.map(extract_for_text, texts))
    execution_time = time.time() - execution_start
    
    # Time the result aggregation
    aggregation_start = time.time()
    for i, chunk in enumerate(chunk_dicts):
        filtered_keywords = keywords_results[i]
        chunk['metadata']['keywords'] = filtered_keywords
        all_keywords.update(filtered_keywords)
    aggregation_time = time.time() - aggregation_start
    
    total_time = time.time() - start_time
    avg_time_per_chunk = execution_time / chunk_count if chunk_count > 0 else 0
    
    print(f"[KEYWORDS] TIMING BREAKDOWN:")
    print(f"[KEYWORDS]   Model loading: {model_load_time:.3f}s")
    print(f"[KEYWORDS]   Text prep: {prep_time:.3f}s")
    print(f"[KEYWORDS]   Parallel execution: {execution_time:.3f}s")
    print(f"[KEYWORDS]   Result aggregation: {aggregation_time:.3f}s")
    print(f"[KEYWORDS]   Total time: {total_time:.3f}s")
    print(f"[KEYWORDS]   Average per chunk: {avg_time_per_chunk:.3f}s")
    print(f"[KEYWORDS]   Extracted {len(all_keywords)} unique keywords")
    
    return chunk_dicts, all_keywords
