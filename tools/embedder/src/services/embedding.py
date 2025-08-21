"""
Embedding service module for generating vector embeddings from text.

This module provides functionality to convert text into vector embeddings 
using a pre-trained sentence transformer model. It implements lazy loading
to initialize the model only when needed.
"""

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

from typing import Union, List

_model = None


def get_embedding(texts: Union[str, List[str]]) -> List:
    """
    Generate vector embeddings for one or more text inputs.
    
    Args:
        texts (str or list): A single text string or a list of text strings to embed
        
    Returns:
        list: A list of vector embeddings, each corresponding to an input text
        
    Raises:
        RuntimeError: If model loading fails, with helpful guidance for Windows memory issues
    """
    global _model
    
    # Initialize the model only on first call
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = settings.embedding_model_settings.model_name
            print(f"[EMBEDDING] Loading model: {model_name}")
            _model = SentenceTransformer(model_name, device='cpu')
            print(f"[EMBEDDING] Model loaded successfully")
            
        except OSError as e:
            if "1455" in str(e) or "paging file" in str(e).lower():
                helpful_message = (
                    f"Windows virtual memory error loading embedding model: {e}\n\n"
                    f"QUICK FIX: Restart your PC\n"
                    f"This usually happens after running the system for a long time.\n"
                    f"A restart will clear memory fragmentation and fix the issue.\n\n"
                    f"If restarting doesn't help:\n"
                    f"1. Close other memory-intensive applications\n"
                    f"2. Make sure you have at least 4GB free disk space\n"
                    f"3. Try processing documents one at a time"
                )
                raise RuntimeError(helpful_message) from e
            else:
                raise
                
        except Exception as e:
            raise RuntimeError(f"Failed to load embedding model: {e}") from e
    
    # Convert single string to list if needed
    if isinstance(texts, str):
        texts = [texts]
    
    # Generate embeddings
    try:
        embeddings = _model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
        return embeddings
    except Exception as e:
        raise RuntimeError(f"Failed to generate embeddings: {e}") from e