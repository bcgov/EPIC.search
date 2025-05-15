# Global model instance - loaded only once
_keymodel = None

def get_keywords(text):
    global _keymodel

    # Initialize the model only on first call
    if _keymodel is None:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer 
        # Use a smaller, faster model that still performs well for keyword extraction
        sentence_model = SentenceTransformer('all-mpnet-base-v2')
        _keymodel = KeyBERT(model=sentence_model)
    
    try:
        keywords = _keymodel.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3), 
            use_mmr=True, 
            diversity=1,
            top_n=10  # Limit to top 10 keywords for speed
        )
        words_to_remove = ["project", "projects"]
        filtered_keywords = [(word, score) for (word, score) in keywords if word not in words_to_remove]
        return filtered_keywords
    except Exception as e:
        print(f"Error extracting keywords: {str(e)}")
        # Return empty list as fallback
        return []