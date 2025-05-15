# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
BERT Keyword Extractor module for extracting relevant keywords from text.

This module uses KeyBERT, which leverages BERT embeddings to extract keywords
and keyphrases that best describe a text document. It uses a lazy loading pattern
to initialize the model only when needed, improving startup time.
"""

_keymodel = None


def get_keywords(text):
    """
    Extract the most relevant keywords or keyphrases from the input text.
    
    This function uses the KeyBERT model to extract keywords and keyphrases
    that are semantically relevant to the input text. It uses the Maximal Marginal
    Relevance (MMR) approach to ensure keyword diversity.
    
    Args:
        text (str): The input text to extract keywords from
        
    Returns:
        list: A list of tuples, where each tuple contains a keyword/keyphrase and its relevance score.
              The list is filtered to remove common generic terms like "project".
              
    Note:
        The model is loaded only on the first call to this function, following a lazy loading pattern.
        Uses a dedicated keyword extraction model that can be configured separately from the embedding model.
    """
    global _keymodel

    # Initialize the model only on first call
    if _keymodel is None:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer
        
        # Get model name from keyword extraction settings
        model_name = settings.keyword_extraction_settings.model_name
        
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
        print(f"Error extracting keywords: {str(e)}")
        # Return empty list as fallback
        return []
