from sentence_transformers import SentenceTransformer
import ollama
from app.config.settings import get_settings
# model = SentenceTransformer('nvidia/NV-Embed-v2', trust_remote_code=True)
# model.max_seq_length = 32768
# model.tokenizer.padding_side="right"

# def get_embedding(text):
#    return model.encode(text)

def get_embedding(text):
    settings = get_settings()
    embedding = ollama.embed(
                 input=text,
                  model=settings.embedding_model.model_name,
             )
    
    return embedding.embeddings