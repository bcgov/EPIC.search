# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
Embedding service module for generating vector embeddings from text.

This module provides functionality to convert text into vector embeddings 
using a pre-trained sentence transformer model. It implements lazy loading
to initialize the model only when needed. This model is specifically used
for document embedding and is separate from the keyword extraction model.
"""

_model = None

def get_embedding(texts):
    """
    Generate vector embeddings for one or more text inputs.
    
    This function lazily loads the embedding model on first call and then 
    uses it to generate embeddings for the provided text(s).
    
    Args:
        texts (str or list): A single text string or a list of text strings to embed
        
    Returns:
        list: A list of vector embeddings, each corresponding to an input text
        
    Note:
        The model used for embeddings is specified in configuration settings
        through the embedding_model_settings and is loaded only once for efficiency.
        This model is specifically optimized for document embedding tasks and
        may differ from the keyword extraction model.
    """
    global _model
    
    # Initialize the model only on first call
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_name = settings.embedding_model_settings.model_name
        _model = SentenceTransformer(model_name) #, device='cuda') - compile with cuda if possible
    
    # Convert single string to list if needed
    if isinstance(texts, str):
        texts = [texts]
        
    # Generate embeddings
    embeddings = _model.encode(texts)
    
    return embeddings