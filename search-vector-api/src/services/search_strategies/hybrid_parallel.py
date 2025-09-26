"""Hybrid Parallel search strategy implementation.

This strategy implements parallel execution of semantic and keyword searches
with result merging and deduplication for comprehensive coverage.
"""

import logging
import time
import threading
import queue
import pandas as pd
from flask import current_app
from typing import Tuple, List, Optional, Dict, Any

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory


class HybridParallelStrategy(BaseSearchStrategy):
    """Hybrid parallel search strategy running semantic and keyword searches simultaneously.
    
    This strategy maximizes coverage by running both search types in parallel
    and then merging the results:
    
    Stage 1: Run semantic and keyword searches in parallel
    Stage 2: Merge results from both searches with deduplication
    Stage 3: Cross-encoder re-ranking for optimal relevance ordering
    """
    
    @property
    def strategy_name(self) -> str:
        return "HYBRID_PARALLEL"
    
    @property
    def description(self) -> str:
        return ("Parallel execution of semantic and keyword searches with result merging "
                "and deduplication. Maximizes coverage by combining both search approaches "
                "while optimizing execution time through parallel processing.")
    
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
        start_time: float = None,
        semantic_query: Optional[str] = None
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Execute the hybrid parallel search strategy.
        
        Args:
            question (str): The search query
            vec_store: Vector store instance
            project_ids (list, optional): Project IDs for filtering
            document_type_ids (list, optional): Document type IDs for filtering
            doc_limit (int, optional): Document search limit (not used in parallel strategy)
            chunk_limit (int, optional): Chunk search limit per search type
            top_n (int, optional): Final result count
            min_relevance_score (float, optional): Minimum relevance threshold
            metrics (dict): Metrics dictionary to update
            start_time (float): Search start time
            semantic_query (str, optional): Pre-optimized semantic query for vector search.
                                          If provided, this takes precedence over question for vector operations.
            
        Returns:
            tuple: (formatted_data, metrics)
        """
        # Import required functions from the main vector_search module
        from ..vector_search import (
            perform_semantic_search_all_chunks,
            perform_keyword_search,
            perform_reranking,
            format_data
        )
        
        # Determine the query to use for semantic search operations
        # Use semantic_query if provided, otherwise fall back to question
        search_query = semantic_query if semantic_query is not None else question
        
        # Validate parameters
        self._validate_parameters(question, vec_store, top_n, min_relevance_score)
        
        # Initialize metrics if not provided
        if metrics is None:
            metrics = {}
        
        # Log strategy start
        self._log_strategy_start(question, project_ids, document_type_ids)
        logging.info("HYBRID_PARALLEL - Starting parallel semantic and keyword searches")
        
        # Capture the Flask application context for use in threads
        app_context = current_app._get_current_object()
        vector_table_name = current_app.vector_settings.vector_table_name
        
        # Results queue for threading
        results_queue = queue.Queue()
        
        def semantic_search_worker():
            worker_start = time.time()
            try:
                with app_context.app_context():
                    logging.debug("HYBRID_PARALLEL - Semantic worker starting")
                    semantic_results, semantic_time = perform_semantic_search_all_chunks(
                        vec_store, search_query, chunk_limit, project_ids, document_type_ids
                    )
                    logging.debug(f"HYBRID_PARALLEL - Semantic worker completed in {time.time() - worker_start:.2f}s")
                    results_queue.put(("semantic", semantic_results, semantic_time))
            except Exception as e:
                worker_time = time.time() - worker_start
                logging.error(f"HYBRID_PARALLEL - Semantic search worker failed after {worker_time:.2f}s: {e}")
                logging.exception("HYBRID_PARALLEL - Semantic worker exception details:")
                try:
                    results_queue.put(("semantic", pd.DataFrame(), 0))
                except Exception as queue_error:
                    logging.error(f"HYBRID_PARALLEL - Failed to put semantic error result in queue: {queue_error}")
        
        def keyword_search_worker():
            worker_start = time.time()
            try:
                with app_context.app_context():
                    logging.debug("HYBRID_PARALLEL - Keyword worker starting")
                    keyword_results, keyword_time = perform_keyword_search(
                        vec_store, vector_table_name, question, chunk_limit, project_ids, document_type_ids
                    )
                    logging.debug(f"HYBRID_PARALLEL - Keyword worker completed in {time.time() - worker_start:.2f}s")
                    results_queue.put(("keyword", keyword_results, keyword_time))
            except Exception as e:
                worker_time = time.time() - worker_start
                logging.error(f"HYBRID_PARALLEL - Keyword search worker failed after {worker_time:.2f}s: {e}")
                logging.exception("HYBRID_PARALLEL - Keyword worker exception details:")
                try:
                    results_queue.put(("keyword", pd.DataFrame(), 0))
                except Exception as queue_error:
                    logging.error(f"HYBRID_PARALLEL - Failed to put keyword error result in queue: {queue_error}")
        
        # Start both search threads
        semantic_thread = threading.Thread(target=semantic_search_worker, name="SemanticSearch")
        keyword_thread = threading.Thread(target=keyword_search_worker, name="KeywordSearch")
        
        parallel_start = time.time()
        semantic_thread.start()
        keyword_thread.start()
        
        # Wait for both searches to complete with timeout
        # Get timeout from configuration to prevent indefinite hanging
        timeout_seconds = current_app.search_settings.parallel_search_timeout
        
        # Use separate timeouts and better thread management
        semantic_completed = False
        keyword_completed = False
        
        # Join threads with individual timeout tracking
        semantic_thread.join(timeout=timeout_seconds)
        semantic_completed = not semantic_thread.is_alive()
        
        keyword_thread.join(timeout=timeout_seconds)
        keyword_completed = not keyword_thread.is_alive()
        
        # Log thread completion status
        if not semantic_completed:
            logging.error("HYBRID_PARALLEL - Semantic search thread timed out after %d seconds", timeout_seconds)
        if not keyword_completed:
            logging.error("HYBRID_PARALLEL - Keyword search thread timed out after %d seconds", timeout_seconds)
        
        parallel_time = self._calculate_elapsed_time(parallel_start)
        
        # Collect results with proper synchronization
        # Use a more robust approach to collect results
        semantic_results = pd.DataFrame()
        keyword_results = pd.DataFrame()
        semantic_time = 0
        keyword_time = 0
        
        # Collect results with timeout to avoid hanging on queue operations
        collected_results = []
        collection_timeout = current_app.search_settings.parallel_result_collection_timeout
        collection_start = time.time()
        
        while len(collected_results) < 2 and (time.time() - collection_start) < collection_timeout:
            try:
                # Non-blocking get with short timeout
                search_type, results, search_time = results_queue.get(timeout=1.0)
                collected_results.append((search_type, results, search_time))
            except queue.Empty:
                # Check if we're still waiting for threads to complete
                if semantic_completed and keyword_completed:
                    break
                continue
        
        # Process collected results
        for search_type, results, search_time in collected_results:
            if search_type == "semantic":
                semantic_results = results
                semantic_time = search_time
            elif search_type == "keyword":
                keyword_results = results
                keyword_time = search_time
        
        # Check if parallel execution failed completely
        both_searches_failed = (
            (not semantic_completed or semantic_results.empty) and 
            (not keyword_completed or keyword_results.empty)
        )
        
        # Fallback to sequential execution if parallel execution failed
        enable_fallback = current_app.search_settings.enable_parallel_fallback
        if both_searches_failed and enable_fallback:
            logging.warning("HYBRID_PARALLEL - Both parallel searches failed/timed out, falling back to sequential execution")
            
            # Try semantic search first
            if semantic_results.empty:
                try:
                    logging.info("HYBRID_PARALLEL - Retrying semantic search sequentially")
                    semantic_results, semantic_time = perform_semantic_search_all_chunks(
                        vec_store, search_query, chunk_limit, project_ids, document_type_ids
                    )
                except Exception as e:
                    logging.error(f"HYBRID_PARALLEL - Sequential semantic search also failed: {e}")
                    semantic_results = pd.DataFrame()
                    semantic_time = 0
            
            # Try keyword search
            if keyword_results.empty:
                try:
                    logging.info("HYBRID_PARALLEL - Retrying keyword search sequentially")
                    keyword_results, keyword_time = perform_keyword_search(
                        vec_store, vector_table_name, question, chunk_limit, project_ids, document_type_ids
                    )
                except Exception as e:
                    logging.error(f"HYBRID_PARALLEL - Sequential keyword search also failed: {e}")
                    keyword_results = pd.DataFrame()
                    keyword_time = 0
        elif both_searches_failed and not enable_fallback:
            logging.error("HYBRID_PARALLEL - Both parallel searches failed/timed out, but fallback is disabled")
        else:
            # Handle individual timeouts
            if not semantic_completed and semantic_results.empty:
                logging.warning("HYBRID_PARALLEL - Using empty semantic results due to timeout")
                semantic_time = 0
            
            if not keyword_completed and keyword_results.empty:
                logging.warning("HYBRID_PARALLEL - Using empty keyword results due to timeout")
                keyword_time = 0
        
        metrics["semantic_search_ms"] = semantic_time
        metrics["keyword_search_ms"] = keyword_time
        metrics["parallel_execution_ms"] = parallel_time
        metrics["parallel_semantic_completed"] = semantic_completed
        metrics["parallel_keyword_completed"] = keyword_completed
        metrics["used_fallback_sequential"] = both_searches_failed
        
        semantic_count = len(semantic_results) if not semantic_results.empty else 0
        keyword_count = len(keyword_results) if not keyword_results.empty else 0
        logging.info(f"HYBRID_PARALLEL - Semantic: {semantic_count} chunks (completed: {semantic_completed})")
        logging.info(f"HYBRID_PARALLEL - Keyword: {keyword_count} chunks (completed: {keyword_completed})")
        
        # Merge results from both searches
        chunk_results = self._merge_parallel_search_results(semantic_results, keyword_results)
        
        merged_count = len(chunk_results) if not chunk_results.empty else 0
        logging.info(f"HYBRID_PARALLEL - Merged: {merged_count} unique chunks")
        
        # Re-rank combined results using cross-encoder
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
        metrics["search_mode"] = "hybrid_parallel"
        
        # Log completion
        self._log_strategy_completion(len(formatted_data))
        
        return formatted_data, metrics
    
    def _merge_parallel_search_results(self, semantic_results, keyword_results):
        """Merge results from parallel semantic and keyword searches, removing duplicates.
        
        Args:
            semantic_results (DataFrame): Results from semantic search
            keyword_results (DataFrame): Results from keyword search
            
        Returns:
            DataFrame: Merged results with duplicates removed based on chunk ID
        """
        # If one of the results is empty, return the other
        if semantic_results.empty and keyword_results.empty:
            return pd.DataFrame()
        elif semantic_results.empty:
            return keyword_results
        elif keyword_results.empty:
            return semantic_results
        
        # Add search type information to track origin
        semantic_results = semantic_results.copy()
        keyword_results = keyword_results.copy()
        semantic_results["search_type"] = "semantic"
        keyword_results["search_type"] = "keyword"
        
        # Combine the DataFrames
        combined_results = pd.concat([semantic_results, keyword_results], ignore_index=True)
        
        # Remove duplicates based on 'id' column (chunk ID), keeping the first occurrence
        # This means semantic results will be preferred over keyword results for duplicates
        if 'id' in combined_results.columns:
            combined_results = combined_results.drop_duplicates(subset=['id'], keep='first')
        
        return combined_results


# Register this strategy with the factory
SearchStrategyFactory.register_strategy("HYBRID_PARALLEL", HybridParallelStrategy)
