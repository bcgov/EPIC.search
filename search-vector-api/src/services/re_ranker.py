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

def rerank_results(query: str, items: pd.DataFrame, top_n: int, batch_size: int = 32, min_relevance_score: float = None) -> pd.DataFrame:
    """Re-rank search results using a cross-encoder model for improved relevance.
    
    This function takes search results from the initial keyword and vector search
    and re-ranks them using a more computationally intensive but more accurate
    cross-encoder model, which scores each query-document pair together.
    
    Args:
        query (str): The original search query text
        items (pd.DataFrame): DataFrame containing the search results to re-rank
        top_n (int): Number of top results to return after re-ranking
        batch_size (int): Batch size for processing document pairs (default: 32)
        min_relevance_score (float, optional): Minimum relevance score threshold for results. If None, uses config/env value.
        
    Returns:
        pd.DataFrame: A DataFrame with the top N re-ranked results sorted by relevance score
        
    Note:
        The returned DataFrame includes a new 'relevance_score' column that
        indicates the cross-encoder's confidence in the relevance of each document.
    """
    import logging
    
    # Check for empty input
    if items.empty:
        logging.warning("rerank_results received empty DataFrame!")
        return items
    
    # Use the cached model instead of creating a new one each time
    model = get_cross_encoder()
    
    documents = items["content"].tolist()
    pairs = [[query, doc] for doc in documents]
    # The relevance score is a float value output by the cross-encoder model's predict method.
    # It represents the model's confidence in the relevance of each document to the query.
    # Higher scores indicate greater relevance. The score's range and interpretation depend on the model,
    # but typically higher is better. This value is used for filtering and sorting results.
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

    # Determine min_relevance_score from config/env if not provided
    if min_relevance_score is None:
        min_relevance_score = float(getattr(current_app.config, "MIN_RELEVANCE_SCORE", -10.0))
    
    # Filter by min_relevance_score
    filtered_df = sorted_df[sorted_df["relevance_score"] >= min_relevance_score]
    
    top_n_records = filtered_df.head(int(top_n))

    return top_n_records
