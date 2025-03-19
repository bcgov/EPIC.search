# Global model instance - loaded only once
import os


_model = None

def get_embedding(texts):
    global _model
    
    # Initialize the model only on first call
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(os.getenv("SENTENCE_TRANSFORMER_MODEL", 'all-mpnet-base-v2'))
    
    # Convert single string to list if needed
    if isinstance(texts, str):
        texts = [texts]
        
    # Generate embeddings with a timeout to prevent hanging
    try:
        embeddings = _model.encode(texts, show_progress_bar=False)
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        # Return zero embeddings as fallback
        import numpy as np
        return np.zeros((len(texts), 768))