import time
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
from transformers import pipeline

def download_models():
    print("Pre-downloading NLP models...")
    start_time = time.time()
    
    # Pre-download the sentence transformer model
    print("Downloading sentence-transformer model...")
    sentence_model = SentenceTransformer('all-mpnet-base-v2')
    print(f"Downloaded sentence-transformer model in {time.time() - start_time:.2f} seconds")
    
    # Initialize KeyBERT with the model
    print("Initializing KeyBERT...")
    keybert_start = time.time()
    _ = KeyBERT(model=sentence_model)
    print(f"Initialized KeyBERT in {time.time() - keybert_start:.2f} seconds")
    
    # Pre-download the NER model
    print("Downloading NER model...")
    ner_start_time = time.time()
    ner = pipeline(
        "ner", 
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        revision="f2482bf",
        aggregation_strategy="simple"  # Using the recommended parameter instead of grouped_entities
    )
    print(f"Downloaded NER model in {time.time() - ner_start_time:.2f} seconds")

    # You can test the model to ensure it's properly loaded
    _ = ner("Claude is an AI assistant created by Anthropic.")
        
    print("All models downloaded successfully!")
    print(f"Total initialization time: {time.time() - start_time:.2f} seconds")
    
if __name__ == "__main__":
    download_models()