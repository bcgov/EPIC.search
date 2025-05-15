import os
import time
import sys
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

"""
Model Preloader for EPIC.search Embedder.

This module provides functionality to pre-download and initialize NLP models 
before they are needed in the application. This helps to avoid delays during 
runtime processing, especially in environments like containers where first-run 
model downloads can cause significant latency.

Two distinct models can be preloaded:
1. The embedding model used for document vectorization
2. The keyword extraction model used for identifying key terms
"""

def download_models():
    """
    Download and initialize NLP models required by the application.
    
    This function pre-downloads both the embedding model and keyword extraction model
    specified in the environment variables and initializes the KeyBERT model.
    It prints progress information and timing statistics during the download process.
    
    Models downloaded:
    - Embedding model for document vector embeddings (EMBEDDING_MODEL_NAME)
    - Keyword extraction model for extracting key terms (KEYWORD_MODEL_NAME)
    
    Returns:
        None
        
    Raises:
        SystemExit: If required environment variables are not provided
    """
    print("Pre-downloading NLP models...")
    start_time = time.time()
    
    # Pre-download the embedding model
    print("Downloading embedding model...")
    embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME")
    if embedding_model_name is None:
        print("ERROR: EMBEDDING_MODEL_NAME environment variable is required.")
        print("Please set this environment variable or pass it as a build argument.")
        sys.exit(1)
            
    embedding_transformer = SentenceTransformer(embedding_model_name)
    print(f"Downloaded embedding model in {time.time() - start_time:.2f} seconds")
    
    # Pre-download the keyword extraction model
    print("Downloading keyword extraction model...")
    keyword_model_start = time.time()
    keyword_model_name = os.getenv("KEYWORD_MODEL_NAME")
    if keyword_model_name is None:
        # Default to embedding model if no specific keyword model is provided
        print("KEYWORD_MODEL_NAME not specified, using embedding model for keyword extraction as well.")
        keyword_model_name = embedding_model_name
        keyword_transformer = embedding_transformer  # Reuse the same model instance
    else:
        # Download specific keyword model if different from embedding model
        if keyword_model_name == embedding_model_name:
            print("Keyword model is the same as embedding model, reusing...")
            keyword_transformer = embedding_transformer
        else:
            print(f"Downloading separate keyword model: {keyword_model_name}")
            keyword_transformer = SentenceTransformer(keyword_model_name)
            
    print(f"Downloaded keyword model in {time.time() - keyword_model_start:.2f} seconds")
    
    # Initialize KeyBERT with the keyword model
    print("Initializing KeyBERT...")
    keybert_start = time.time()
    _ = KeyBERT(model=keyword_transformer)
    print(f"Initialized KeyBERT in {time.time() - keybert_start:.2f} seconds")

    print("All models downloaded successfully!")
    print(f"Total initialization time: {time.time() - start_time:.2f} seconds")
    
if __name__ == "__main__":
    download_models()