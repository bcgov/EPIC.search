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
    global _keymodel, _sentence_model
    if _keymodel is None or _sentence_model is None:
        model_name = settings.keyword_extraction_settings.model_name
        _sentence_model = SentenceTransformer(model_name)
        _keymodel = KeyBERT(model=_sentence_model)
    texts = [chunk['content'] for chunk in chunk_dicts]
    if not texts:
        return chunk_dicts, set()
    all_keywords = set()
    def extract_for_text(text):
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            use_mmr=True,
            diversity=0.7,
            top_n=5
        )
        words_to_remove = ["project", "projects"]
        return [word for word, score in keywords if word not in words_to_remove]
    # Parallelize extraction across chunks
    with ThreadPoolExecutor() as executor:
        keywords_results = list(executor.map(extract_for_text, texts))
    for i, chunk in enumerate(chunk_dicts):
        filtered_keywords = keywords_results[i]
        chunk['metadata']['keywords'] = filtered_keywords
        all_keywords.update(filtered_keywords)
    return chunk_dicts, all_keywords
