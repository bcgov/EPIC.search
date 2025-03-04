# Global model instance - loaded only once
_model = None

def get_embedding(texts):
    global _model
    
    # Initialize the model only on first call
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-mpnet-base-v2') #, device='cuda') - compile with cuda if possible
    
    # Convert single string to list if needed
    if isinstance(texts, str):
        texts = [texts]
        
    # Generate embeddings
    embeddings = _model.encode(texts)
    
    return embeddings