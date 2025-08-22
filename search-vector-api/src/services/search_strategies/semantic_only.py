"""Semantic Only search strategy implementation.

This strategy implements pure semantic search without keyword filtering or fallbacks,
optimized for semantic similarity and conceptual matching.
"""

import logging
import time
from typing import Tuple, List, Optional, Dict, Any

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory


class SemanticOnlyStrategy(BaseSearchStrategy):
    """Pure semantic search strategy without keyword components.
    
    This strategy focuses entirely on semantic similarity matching using
    vector embeddings, without any keyword-based filtering or fallbacks:
    
    Stage 1: Semantic search directly across all chunks
    Stage 2: Apply project and document type filtering
    Stage 3: Cross-encoder re-ranking for optimal relevance ordering
    """
    
    @property
    def strategy_name(self) -> str:
        return "SEMANTIC_ONLY"
    
    @property
    def description(self) -> str:
        return ("Pure semantic search using vector embeddings across all chunks "
                "with project and document type filtering. Optimized for conceptual "
                "and semantic similarity matching without keyword dependencies.")
    
    def execute(
        self, 
        question: str, 
        vec_store, 
        project_ids: Optional[List[str]] = None, 
        document_type_ids: Optional[List[str]] = None, 
        doc_limit: Optional[int] = None, 
        chunk_limit: Optional[int] = None, 
        top_n: Optional[int] = None, 
        min_relevance_score: Optional[float] = None, 
        metrics: Dict[str, Any] = None, 
        start_time: float = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Execute the semantic only search strategy.
        
        Args:
            question (str): The search query
            vec_store: Vector store instance
            project_ids (list, optional): Project IDs for filtering
            document_type_ids (list, optional): Document type IDs for filtering
            doc_limit (int, optional): Document search limit (not used in this strategy)
            chunk_limit (int, optional): Chunk search limit
            top_n (int, optional): Final result count
            min_relevance_score (float, optional): Minimum relevance threshold
            metrics (dict): Metrics dictionary to update
            start_time (float): Search start time
            
        Returns:
            tuple: (formatted_data, metrics)
        """
        # Import required functions from the main vector_search module
        from ..vector_search import (
            perform_semantic_search_all_chunks,
            perform_reranking,
            format_data
        )
        
        # Validate parameters
        self._validate_parameters(question, vec_store, top_n, min_relevance_score)
        
        # Initialize metrics if not provided
        if metrics is None:
            metrics = {}
        
        # Log strategy start
        self._log_strategy_start(question, project_ids, document_type_ids)
        logging.info("SEMANTIC_ONLY - Starting pure semantic search")
        
        # Perform semantic search across all chunks with project and document type filtering
        chunk_results, semantic_search_time = perform_semantic_search_all_chunks(
            vec_store, question, chunk_limit, project_ids, document_type_ids
        )
        metrics["semantic_search_ms"] = semantic_search_time
        
        chunk_count = len(chunk_results) if not chunk_results.empty else 0
        logging.info(f"SEMANTIC_ONLY - Found {chunk_count} chunks")
        
        # Re-rank results using cross-encoder
        reranked_results, rerank_time, filtering_metrics = perform_reranking(
            question, chunk_results, top_n, min_relevance_score
        )
        metrics["reranking_ms"] = rerank_time
        
        # Add filtering metrics to the search metrics
        metrics.update({
            "filtering_total_chunks": filtering_metrics["total_chunks_before_filtering"],
            "filtering_excluded_chunks": filtering_metrics["excluded_chunks_count"],
            "filtering_exclusion_percentage": filtering_metrics["exclusion_percentage"],
            "filtering_final_chunks": filtering_metrics["final_chunk_count"]
        })
        
        # Add score range information if available
        if filtering_metrics["score_range_excluded"]:
            metrics["filtering_excluded_score_range"] = filtering_metrics["score_range_excluded"]
        if filtering_metrics["score_range_included"]:
            metrics["filtering_included_score_range"] = filtering_metrics["score_range_included"]
        
        results = reranked_results
        
        # Format the data
        format_start = time.time()
        formatted_data = format_data(results)
        metrics["formatting_ms"] = self._calculate_elapsed_time(format_start)
        
        # Total time
        if start_time is not None:
            metrics["total_search_ms"] = self._calculate_elapsed_time(start_time)
        metrics["search_mode"] = "semantic_only"
        
        # Log completion
        self._log_strategy_completion(len(formatted_data))
        
        return formatted_data, metrics


# Register this strategy with the factory
SearchStrategyFactory.register_strategy("SEMANTIC_ONLY", SemanticOnlyStrategy)
