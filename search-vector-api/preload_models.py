import os
import time
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT

def download_models():
    print("Pre-downloading NLP models...")
    start_time = time.time()
    
    # Pre-download the sentence transformer model
    print("Downloading sentence-transformer model...")
    sentence_model = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-mpnet-base-v2")
    sentence_transformer = SentenceTransformer(sentence_model)
    print(f"Downloaded sentence-transformer model in {time.time() - start_time:.2f} seconds")
    
    # Initialize KeyBERT with the model
    print("Initializing KeyBERT...")
    keybert_start = time.time()
    _ = KeyBERT(model=sentence_transformer)
    print(f"Initialized KeyBERT in {time.time() - keybert_start:.2f} seconds")
    
    # Pre-download the NER model
    print("Downloading NER model...")
    ner_start_time = time.time()
    print(f"Downloaded NER model in {time.time() - ner_start_time:.2f} seconds")

    print("All models downloaded successfully!")
    print(f"Total initialization time: {time.time() - start_time:.2f} seconds")
    
if __name__ == "__main__":
    download_models()