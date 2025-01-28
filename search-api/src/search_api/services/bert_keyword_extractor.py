from keybert import KeyBERT

def get_keywords(text):
    kw_model = KeyBERT()
    keywords = kw_model.extract_keywords(text,keyphrase_ngram_range=(1, 3), use_mmr=True, diversity=1)
    words_to_remove = ["project", "projects"]
    filtered_keywords = [(word, score) for (word, score) in keywords if word not in words_to_remove]
    return filtered_keywords