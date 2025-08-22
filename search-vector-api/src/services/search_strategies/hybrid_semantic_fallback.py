"""Hybrid Semantic Fallback search strategy implementation.

This strategy implements a multi-stage search approach with semantic search as the primary
method and keyword search as a fallback, optimized for high-quality results.
"""

import logging
import time
from flask import current_app
from typing import Tuple, List, Optional, Dict, Any

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory


def perform_chunk_search_within_documents(vec_store, document_ids, query, limit):
    """Perform semantic search within specific documents' chunks.
    
    Searches the document_chunks table for the most relevant chunks,
    but only within the chunks belonging to the specified documents.
    
    Args:
        vec_store (VectorStore): The vector store instance
        document_ids (list): List of document IDs to search within
        query (str): The search query text
        limit (int): Maximum number of chunks to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Chunk search results with id, content, metadata columns
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Perform chunk search within specific documents
    chunk_results = vec_store.search_chunks_by_documents(
        document_ids, query, limit=limit, return_dataframe=True
    )
    
    # Rename columns to match expected format for format_data function
    if not chunk_results.empty:
        # The search_chunks_by_documents returns: [id, metadata, content, document_id, project_id, similarity]
        chunk_results["search_type"] = "semantic"
        
        # Add empty document_metadata column for compatibility with format_data function
        # Note: We'll populate document_type in the format_data function using chunk metadata when possible
        chunk_results["document_metadata"] = [{}] * len(chunk_results)
        
        # Reorder to match expected structure: id, content, search_type, similarity, metadata, document_metadata
        chunk_results = chunk_results[["id", "content", "search_type", "similarity", "metadata", "document_metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return chunk_results, elapsed_ms


class HybridSemanticFallbackStrategy(BaseSearchStrategy):
    """Hybrid search strategy with semantic search and keyword fallback.
    
    This is the default search strategy that provides optimal balance between
    efficiency and result quality through a multi-stage approach:
    
    Stage 1: Document-level keyword filtering for efficiency
    Stage 2: Semantic search within relevant documents for quality
    Fallback 2.1: Semantic search across all chunks if no documents found
    Fallback 2.2: Keyword search if semantic search fails
    Stage 3: Cross-encoder re-ranking for optimal relevance ordering
    """
    
    @property
    def strategy_name(self) -> str:
        return "HYBRID_SEMANTIC_FALLBACK"
    
    @property
    def description(self) -> str:
        return ("Multi-stage hybrid search with document filtering, semantic search within "
                "relevant documents, semantic fallback across all chunks, and keyword fallback "
                "as last resort. Optimized for high-quality results with efficiency.")
    
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
        """Execute the hybrid semantic fallback search strategy.
        
        Args:
            question (str): The search query
            vec_store: Vector store instance
            project_ids (list, optional): Project IDs for filtering
            document_type_ids (list, optional): Document type IDs for filtering
            doc_limit (int, optional): Document search limit
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
            perform_document_level_search,
            perform_semantic_search_all_chunks,
            perform_keyword_search,
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
        
        # Stage 1: Find relevant documents using document-level metadata
        relevant_documents, doc_search_time = perform_document_level_search(
            vec_store, question, doc_limit, project_ids, document_type_ids
        )
        metrics["document_search_ms"] = doc_search_time
        
        # Debug logging
        document_count = len(relevant_documents) if not relevant_documents.empty else 0
        logging.info(f"HYBRID_SEMANTIC_FALLBACK - Stage 1: Found {document_count} documents")
        
        # Stage 2: Search chunks within the relevant documents
        if not relevant_documents.empty:
            document_ids = relevant_documents["document_id"].tolist()
            chunk_results, chunk_search_time = perform_chunk_search_within_documents(
                vec_store, document_ids, question, chunk_limit
            )
            metrics["chunk_search_ms"] = chunk_search_time
            chunk_count = len(chunk_results) if not chunk_results.empty else 0
            logging.info(f"HYBRID_SEMANTIC_FALLBACK - Stage 2: Found {chunk_count} chunks in documents")
        else:
            # Alternative path: if no documents found, perform semantic search across all chunks
            logging.info("HYBRID_SEMANTIC_FALLBACK - Stage 2: No documents found, using semantic search across all chunks")
            chunk_results, semantic_search_time = perform_semantic_search_all_chunks(
                vec_store, question, chunk_limit, project_ids, document_type_ids
            )
            metrics["semantic_search_ms"] = semantic_search_time
            chunk_count = len(chunk_results) if not chunk_results.empty else 0
            logging.info(f"HYBRID_SEMANTIC_FALLBACK - Semantic fallback found {chunk_count} chunks")
        
        # If both document search and semantic search returned no results, try keyword search
        if chunk_results.empty:
            logging.info("HYBRID_SEMANTIC_FALLBACK - Stage 3: Semantic search returned no results, trying keyword search as last resort")
            try:
                table_name = current_app.vector_settings.vector_table_name
                keyword_results, keyword_time = perform_keyword_search(
                    vec_store, table_name, question, chunk_limit, project_ids, document_type_ids
                )
                if not keyword_results.empty:
                    chunk_results = keyword_results
                    metrics["keyword_fallback_ms"] = keyword_time
                    fallback_count = len(chunk_results)
                    logging.info(f"HYBRID_SEMANTIC_FALLBACK - Keyword fallback found {fallback_count} chunks")
                else:
                    logging.info("HYBRID_SEMANTIC_FALLBACK - Keyword fallback also returned no results")
            except Exception as e:
                logging.error(f"HYBRID_SEMANTIC_FALLBACK - Keyword fallback search failed: {e}")
        
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
        metrics["search_mode"] = "hybrid_semantic_fallback"
        
        # Log completion
        self._log_strategy_completion(len(formatted_data))
        
        return formatted_data, metrics


# Register this strategy with the factory
SearchStrategyFactory.register_strategy("HYBRID_SEMANTIC_FALLBACK", HybridSemanticFallbackStrategy)
