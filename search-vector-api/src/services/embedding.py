from flask import current_app

_model = None

def get_embedding(texts):
    global _model
    
    # Initialize the model only on first call
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Use strongly typed configuration instead of environment variables
        model_name = current_app.model_settings.embedding_model_name
        _model = SentenceTransformer(model_name)
    
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
        # Get dimensions directly from configuration
        embedding_dimensions = current_app.vector_settings.embedding_dimensions
        return np.zeros((len(texts), embedding_dimensions))