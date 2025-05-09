import os
import time
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
from sentence_transformers import CrossEncoder

"""
Pre-downloads and initializes NLP models for the search-vector-api.

This script loads three types of models used by the API:
1. Sentence Transformer Model - For generating vector embeddings from text
2. KeyBERT Model - For extracting keywords from text queries
3. CrossEncoder Model - For re-ranking search results based on relevance

All models must be specified via environment variables when this script is called.
No default fallback values are provided to ensure explicit configuration.

Environment variables:
- EMBEDDING_MODEL_NAME: The sentence transformer model to use for embeddings
- KEYWORD_MODEL_NAME: The model to use for keyword extraction (typically same as embedding)
- CROSS_ENCODER_MODEL: The cross-encoder model to use for re-ranking results

Example usage:
$ EMBEDDING_MODEL_NAME="all-mpnet-base-v2" KEYWORD_MODEL_NAME="all-mpnet-base-v2" CROSS_ENCODER_MODEL="cross-encoder/ms-marco-MiniLM-L-2-v2" python preload_models.py
"""

def download_models():
    """
    Downloads and initializes NLP models required by the search API.
    
    Raises:
        ValueError: If any required model environment variable is not set
    """
    print("Pre-downloading NLP models...")
    start_time = time.time()
    
    # Pre-download the sentence transformer model for embeddings
    print("Downloading sentence-transformer model...")
    sentence_model = os.getenv("EMBEDDING_MODEL_NAME")
    if not sentence_model:
        raise ValueError("EMBEDDING_MODEL_NAME environment variable must be set")
    
    embedding_start = time.time()
    sentence_transformer = SentenceTransformer(sentence_model)
    print(f"Downloaded sentence-transformer model in {time.time() - embedding_start:.2f} seconds")
    
    # Initialize KeyBERT with the model
    print("Initializing KeyBERT...")
    keyword_model = os.getenv("KEYWORD_MODEL_NAME")
    if not keyword_model:
        raise ValueError("KEYWORD_MODEL_NAME environment variable must be set")
    
    keybert_start = time.time()
    # If keyword model is different from sentence model, load it separately
    if keyword_model == sentence_model:
        _ = KeyBERT(model=sentence_transformer)
    else:
        _ = KeyBERT(model=keyword_model)
    print(f"Initialized KeyBERT in {time.time() - keybert_start:.2f} seconds")
    
    # Pre-download the CrossEncoder model for re-ranking
    print("Downloading CrossEncoder model for re-ranking...")
    cross_encoder_model = os.getenv("CROSS_ENCODER_MODEL")
    if not cross_encoder_model:
        raise ValueError("CROSS_ENCODER_MODEL environment variable must be set")
    
    cross_encoder_start = time.time()
    _ = CrossEncoder(cross_encoder_model)
    print(f"Downloaded CrossEncoder model in {time.time() - cross_encoder_start:.2f} seconds")

    print("All models downloaded successfully!")
    print(f"Total initialization time: {time.time() - start_time:.2f} seconds")
    
if __name__ == "__main__":
    download_models()