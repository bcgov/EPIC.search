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
from typing import Tuple, Dict, Any

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
        min_relevance_score (float, optional): Minimum relevance score threshold for filtering results.
            If None, uses the MIN_RELEVANCE_SCORE config value (default: -8.0).
            
            Understanding Cross-Encoder Scores:
            - Cross-encoder models produce raw logit scores that can be positive OR negative
            - Higher values indicate greater relevance (relative ranking matters most)
            - Negative scores are NORMAL and often represent relevant documents
            - For ms-marco-MiniLM-L-2-v2 model:
              * Highly relevant: typically -2.0 to +5.0
              * Moderately relevant: typically -6.0 to -2.0  
              * Less relevant: typically -10.0 to -6.0
              * Likely irrelevant: below -10.0
            
            Common threshold values:
            - -8.0 (default): Balanced, filters out likely irrelevant results
            - -5.0: More restrictive, higher quality threshold
            - -2.0: Very restrictive, only most confident matches
            - 0.0: Too restrictive for this model (filters out relevant results)
            - +10.0: Extremely restrictive (would return almost no results)
            
            Adaptive Threshold Logic:
            - If all results score below -9.0, they are considered low-quality matches
            - Results are marked with a 'low_confidence' flag when this occurs
            - This helps distinguish between relevant matches and query mismatches
        
    Returns:
        pd.DataFrame: A DataFrame with the top N re-ranked results sorted by relevance score.
                     Includes 'relevance_score' and 'low_confidence' columns.
        
    Note:
        The returned DataFrame includes a new 'relevance_score' column that
        indicates the cross-encoder's confidence in the relevance of each document.
        When all results have very low scores, a 'low_confidence' flag is added
        to indicate potential query-document mismatch.
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
    
    # Determine min_relevance_score from config/env if not provided
    if min_relevance_score is None:
        min_relevance_score = float(getattr(current_app.config, "MIN_RELEVANCE_SCORE", -8.0))
    
    # Check if all scores are very low (indicating potential query-document mismatch)
    max_score = max(scores) if len(scores) > 0 else -999
    low_confidence_threshold = -9.0
    all_scores_low = max_score < low_confidence_threshold
    
    if all_scores_low:
        logging.info(f"All relevance scores below {low_confidence_threshold} for query: '{query}' (max: {max_score:.2f})")
    
    reranked_df = pd.DataFrame(
        [
            {
                "id": result["id"],
                "content": result["content"],
                "search_type": result["search_type"],
                "relevance_score": scores[i],
                "low_confidence": all_scores_low,
                "metadata": result["metadata"],
            }
            for i, (_, result) in enumerate(items.iterrows())
        ]
    )
    sorted_df = reranked_df.sort_values("relevance_score", ascending=False)

    # Track filtering metrics before applying threshold
    total_chunks_before_filtering = len(sorted_df)
    
    # Filter by min_relevance_score
    filtered_df = sorted_df[sorted_df["relevance_score"] >= min_relevance_score]
    
    # Calculate exclusion metrics
    excluded_chunks_count = total_chunks_before_filtering - len(filtered_df)
    exclusion_percentage = (excluded_chunks_count / total_chunks_before_filtering * 100) if total_chunks_before_filtering > 0 else 0
    
    # Log exclusion statistics
    if excluded_chunks_count > 0:
        logging.info(f"Re-ranking threshold filtering: excluded {excluded_chunks_count}/{total_chunks_before_filtering} chunks ({exclusion_percentage:.1f}%) below threshold {min_relevance_score}")
        if excluded_chunks_count > 0:
            excluded_scores = sorted_df[sorted_df["relevance_score"] < min_relevance_score]["relevance_score"]
            if not excluded_scores.empty:
                logging.debug(f"Excluded chunk score range: {excluded_scores.min():.3f} to {excluded_scores.max():.3f}")
    else:
        logging.debug(f"Re-ranking threshold filtering: no chunks excluded (threshold: {min_relevance_score})")
        
    # Log remaining chunk quality
    if not filtered_df.empty:
        remaining_scores = filtered_df["relevance_score"]
        logging.info(f"Remaining chunks after filtering: {len(filtered_df)} with scores {remaining_scores.min():.3f} to {remaining_scores.max():.3f}")
    
    # If filtering removes all results but we had some initially, log this
    if not filtered_df.empty:
        top_n_records = filtered_df.head(int(top_n))
    else:
        logging.warning(f"All {total_chunks_before_filtering} results filtered out by min_relevance_score={min_relevance_score} for query: '{query}'")
        # Return empty DataFrame with proper structure
        return pd.DataFrame(columns=["id", "content", "search_type", "relevance_score", "low_confidence", "metadata"])

    # Final logging
    final_count = len(top_n_records)
    logging.info(f"Re-ranking complete: {total_chunks_before_filtering} → {len(filtered_df)} → {final_count} (input → filtered → final)")
    
    return top_n_records

def rerank_results_with_metrics(query: str, items: pd.DataFrame, top_n: int, batch_size: int = 32, min_relevance_score: float = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Re-rank search results and return both results and filtering metrics.
    
    This function is identical to rerank_results but also returns detailed metrics
    about the filtering process, including how many chunks were excluded.
    
    Args:
        query (str): The original search query text
        items (pd.DataFrame): DataFrame containing the search results to re-rank
        top_n (int): Number of top results to return after re-ranking
        batch_size (int): Batch size for processing document pairs (default: 32)
        min_relevance_score (float, optional): Minimum relevance score threshold for filtering results.
            If None, uses the MIN_RELEVANCE_SCORE config value (default: -8.0).
        
    Returns:
        tuple: A tuple containing:
            - pd.DataFrame: Re-ranked and filtered results
            - dict: Filtering metrics including:
                - total_chunks_before_filtering: Number of chunks before threshold filtering
                - excluded_chunks_count: Number of chunks excluded by threshold
                - exclusion_percentage: Percentage of chunks excluded
                - final_chunk_count: Number of chunks in final results
                - score_range_excluded: Score range of excluded chunks (if any)
                - score_range_included: Score range of included chunks (if any)
    """
    import logging
    
    # Check for empty input
    if items.empty:
        logging.warning("rerank_results_with_metrics received empty DataFrame!")
        empty_metrics = {
            "total_chunks_before_filtering": 0,
            "excluded_chunks_count": 0,
            "exclusion_percentage": 0.0,
            "final_chunk_count": 0,
            "score_range_excluded": None,
            "score_range_included": None
        }
        return items, empty_metrics

    # Use the cached model instead of creating a new one each time
    model = get_cross_encoder()
    
    documents = items["content"].tolist()
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs, batch_size=batch_size)
    
    # Determine min_relevance_score from config/env if not provided
    if min_relevance_score is None:
        min_relevance_score = float(getattr(current_app.config, "MIN_RELEVANCE_SCORE", -8.0))
    
    # Check if all scores are very low (indicating potential query-document mismatch)
    max_score = max(scores) if len(scores) > 0 else -999
    low_confidence_threshold = -9.0
    all_scores_low = max_score < low_confidence_threshold
    
    if all_scores_low:
        logging.info(f"All relevance scores below {low_confidence_threshold} for query: '{query}' (max: {max_score:.2f})")
    
    reranked_df = pd.DataFrame(
        [
            {
                "id": result["id"],
                "content": result["content"],
                "search_type": result["search_type"],
                "relevance_score": scores[i],
                "low_confidence": all_scores_low,
                "metadata": result["metadata"],
            }
            for i, (_, result) in enumerate(items.iterrows())
        ]
    )
    sorted_df = reranked_df.sort_values("relevance_score", ascending=False)

    # Track filtering metrics before applying threshold
    total_chunks_before = len(sorted_df)
    before_threshold_df = sorted_df.copy()
    
    # Apply relevance score threshold filtering  
    filtered_df = sorted_df[sorted_df["relevance_score"] >= min_relevance_score]
    
    # Calculate metrics after filtering
    excluded_chunks_count = total_chunks_before - len(filtered_df)
    exclusion_percentage = (excluded_chunks_count / total_chunks_before * 100) if total_chunks_before > 0 else 0.0
    final_chunk_count = len(filtered_df)
    
    # Calculate score ranges
    if excluded_chunks_count > 0:
        excluded_scores = before_threshold_df[before_threshold_df["relevance_score"] < min_relevance_score]["relevance_score"]
        score_range_excluded = f"{excluded_scores.min():.3f} to {excluded_scores.max():.3f}" if len(excluded_scores) > 0 else None
    else:
        score_range_excluded = None
        
    if final_chunk_count > 0:
        included_scores = filtered_df["relevance_score"]
        score_range_included = f"{included_scores.min():.3f} to {included_scores.max():.3f}"
    else:
        score_range_included = None

    # Create filtering metrics dictionary
    filtering_metrics = {
        "total_chunks_before_filtering": total_chunks_before,
        "excluded_chunks_count": excluded_chunks_count,
        "exclusion_percentage": exclusion_percentage,
        "final_chunk_count": final_chunk_count,
        "score_range_excluded": score_range_excluded,
        "score_range_included": score_range_included
    }

    # Apply top_n limit after filtering
    final_results = filtered_df.head(top_n) if top_n is not None else filtered_df
    
    # Log filtering metrics if any chunks were excluded
    if excluded_chunks_count > 0:
        logging.info(f"Re-ranking filtered out {excluded_chunks_count}/{total_chunks_before} chunks "
                    f"({exclusion_percentage:.1f}%) below threshold {min_relevance_score}")
        
    return final_results, filtering_metrics
