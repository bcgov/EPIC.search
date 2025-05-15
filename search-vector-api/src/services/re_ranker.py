"""Cross-encoder re-ranking service for improving search result relevance.

This module provides functionality for re-ranking search results using a cross-encoder
model, which evaluates the relevance between a query and each document pair. While
the initial vector and keyword search provide fast candidate retrieval, the cross-encoder
offers a more accurate assessment of relevance at the expense of higher computational cost.

The module implements:
1. Lazy loading and caching of the cross-encoder model for efficient reuse
2. Batch processing for optimal performance
3. Relevance scoring for query-document pairs
4. Re-sorting of results by relevance score

Cross-encoders typically provide better ranking quality than the initial retrieval
models as they process the query and document together rather than independently.
"""

import pandas as pd

from flask import current_app
from sentence_transformers import CrossEncoder
from functools import lru_cache
from typing import List, Dict, Any

@lru_cache(maxsize=1)
def get_cross_encoder():
    """Return a cached instance of the CrossEncoder model.
    
    Uses LRU caching to ensure that the model is only loaded once and 
    reused for subsequent calls, optimizing memory usage and performance.
    
    Returns:
        CrossEncoder: A loaded cross-encoder model ready for inference
    """
    model = current_app.model_settings.cross_encoder_model
    return CrossEncoder(model)

def rerank_results(query: str, items: pd.DataFrame, top_n: int, batch_size: int = 32) -> pd.DataFrame:
    """Re-rank search results using a cross-encoder model for improved relevance.
    
    This function takes search results from the initial keyword and vector search
    and re-ranks them using a more computationally intensive but more accurate
    cross-encoder model, which scores each query-document pair together.
    
    Args:
        query (str): The original search query text
        items (pd.DataFrame): DataFrame containing the search results to re-rank
        top_n (int): Number of top results to return after re-ranking
        batch_size (int): Batch size for processing document pairs (default: 32)
        
    Returns:
        pd.DataFrame: A DataFrame with the top N re-ranked results sorted by relevance score
        
    Note:
        The returned DataFrame includes a new 'relevance_score' column that
        indicates the cross-encoder's confidence in the relevance of each document.
    """
    # Use the cached model instead of creating a new one each time
    model = get_cross_encoder()
    
    documents = items["content"].tolist()
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs, batch_size=batch_size)
    reranked_df = pd.DataFrame(
        [
            {
                "id": result["id"],
                "content": result["content"],
                "search_type": result["search_type"],
                "relevance_score": scores[i],
                "metadata": result["metadata"],
            }
            for i, (_, result) in enumerate(items.iterrows())
        ]
    )
    sorted_df = reranked_df.sort_values("relevance_score", ascending=False)
    top_n_records = sorted_df.head(int(top_n))

    return top_n_records
