"""Hybrid Keyword Fallback search strategy implementation.

This strategy implements a multi-stage search approach with keyword search as the primary
method and semantic search as a fallback, optimized for keyword-based queries.
"""

import logging
import time
from flask import current_app
from typing import Tuple, List, Optional, Dict, Any

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory


class HybridKeywordFallbackStrategy(BaseSearchStrategy):
    """Hybrid search strategy with keyword search and semantic fallback.
    
    This strategy prioritizes keyword matching while maintaining semantic search
    as a fallback option:
    
    Stage 1: Document-level keyword filtering for efficiency
    Stage 2: Keyword search within relevant documents for precision
    Fallback 2.1: Keyword search across all chunks if no documents found
    Fallback 2.2: Semantic search if keyword search fails
    Stage 3: Cross-encoder re-ranking for optimal relevance ordering
    """
    
    @property
    def strategy_name(self) -> str:
        return "HYBRID_KEYWORD_FALLBACK"
    
    @property
    def description(self) -> str:
        return ("Multi-stage hybrid search with document filtering, keyword search within "
                "relevant documents, keyword fallback across all chunks, and semantic fallback "
                "as last resort. Optimized for keyword-based queries.")
    
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
        """Execute the hybrid keyword fallback search strategy.
        
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
            perform_keyword_search,
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
        
        # Stage 1: Find relevant documents using document-level metadata
        relevant_documents, doc_search_time = perform_document_level_search(
            vec_store, question, doc_limit, project_ids, document_type_ids
        )
        metrics["document_search_ms"] = doc_search_time
        
        document_count = len(relevant_documents) if not relevant_documents.empty else 0
        logging.info(f"HYBRID_KEYWORD_FALLBACK - Stage 1: Found {document_count} documents")
        
        # Stage 2: Search chunks within the relevant documents using keyword search
        if not relevant_documents.empty:
            document_ids = relevant_documents["document_id"].tolist()
            # Perform keyword search within the identified documents
            table_name = current_app.vector_settings.vector_table_name
            chunk_results, chunk_search_time = self._perform_keyword_search_within_documents(
                vec_store, table_name, question, chunk_limit, document_ids
            )
            metrics["chunk_search_ms"] = chunk_search_time
            chunk_count = len(chunk_results) if not chunk_results.empty else 0
            logging.info(f"HYBRID_KEYWORD_FALLBACK - Stage 2: Found {chunk_count} chunks in documents")
        else:
            # Alternative path: if no documents found, perform keyword search across all chunks
            logging.info("HYBRID_KEYWORD_FALLBACK - Stage 2: No documents found, using keyword search across all chunks")
            table_name = current_app.vector_settings.vector_table_name
            chunk_results, keyword_search_time = perform_keyword_search(
                vec_store, table_name, question, chunk_limit, project_ids, document_type_ids
            )
            metrics["keyword_search_ms"] = keyword_search_time
            chunk_count = len(chunk_results) if not chunk_results.empty else 0
            logging.info(f"HYBRID_KEYWORD_FALLBACK - Keyword search found {chunk_count} chunks")
        
        # If keyword search returned no results, try semantic search as fallback
        if chunk_results.empty:
            logging.info("HYBRID_KEYWORD_FALLBACK - Stage 3: Keyword search returned no results, trying semantic search as fallback")
            try:
                semantic_results, semantic_time = perform_semantic_search_all_chunks(
                    vec_store, question, chunk_limit, project_ids, document_type_ids
                )
                if not semantic_results.empty:
                    chunk_results = semantic_results
                    metrics["semantic_fallback_ms"] = semantic_time
                    fallback_count = len(chunk_results)
                    logging.info(f"HYBRID_KEYWORD_FALLBACK - Semantic fallback found {fallback_count} chunks")
                else:
                    logging.info("HYBRID_KEYWORD_FALLBACK - Semantic fallback also returned no results")
            except Exception as e:
                logging.error(f"HYBRID_KEYWORD_FALLBACK - Semantic fallback search failed: {e}")
        
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
        metrics["search_mode"] = "hybrid_keyword_fallback"
        
        # Log completion
        self._log_strategy_completion(len(formatted_data))
        
        return formatted_data, metrics

    def _perform_keyword_search_within_documents(self, vec_store, table_name, query, limit, document_ids):
        """Perform keyword search within specific documents.
        
        Executes a keyword-based search using PostgreSQL's full-text search capabilities
        within a specific set of documents. The keyword extraction method used will match
        the method used for document keywords to ensure optimal matching.
        
        Args:
            vec_store (VectorStore): The vector store instance
            table_name (str): The database table to search in
            query (str): The search query text
            limit (int): Maximum number of results to return
            document_ids (list): List of document IDs to search within
            
        Returns:
            tuple: A tuple containing:
                - DataFrame: Search results with id, content, search_type, and metadata columns
                - float: Time taken in milliseconds
        """
        from flask import current_app
        import time
        import logging
        from ..keywords.query_keyword_extractor import get_keywords
        
        # Use the appropriate keyword extraction method based on document configuration
        extraction_method = current_app.model_settings.document_keyword_extraction_method
        
        # Use the get_keywords function which now handles method selection internally
        weighted_keywords = get_keywords(query)
        logging.info(f"Using {extraction_method} keyword extraction for document search: {query}")

        # Extract just the keywords from the (keyword, score) tuples
        keywords_only = [keyword for keyword, score in weighted_keywords] if weighted_keywords else []

        # Pass the extracted keywords to the vector store (without document filtering for now)
        start_time = time.time()
        keyword_results = vec_store.keyword_search(
            table_name, query, limit=limit, return_dataframe=True, 
            weighted_keywords=keywords_only
        )
        
        # Apply document filtering after the search
        if not keyword_results.empty and document_ids:
            keyword_results = self._apply_document_filtering(keyword_results, document_ids)
        
        keyword_results["search_type"] = "keyword"
        
        # Ensure we have the expected columns
        expected_columns = ["id", "content", "search_type", "metadata"]
        available_columns = [col for col in expected_columns if col in keyword_results.columns]
        keyword_results = keyword_results[available_columns]
        
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return keyword_results, elapsed_ms

    def _apply_document_filtering(self, results_df, document_ids):
        """Apply document ID filtering to search results.
        
        This function filters search results to only include chunks from specific documents
        by examining the metadata column in the results DataFrame.
        
        Args:
            results_df (DataFrame): Search results with metadata column
            document_ids (list): List of document IDs to filter by
            
        Returns:
            DataFrame: Filtered search results
        """
        import pandas as pd
        import logging
        
        if results_df.empty or not document_ids:
            return results_df
        
        def matches_document(metadata):
            if not isinstance(metadata, dict):
                return False
            
            # Check if document_id is directly in metadata
            metadata_doc_id = metadata.get('document_id')
            if metadata_doc_id and metadata_doc_id in document_ids:
                return True
            
            # Check if document_id is in document_metadata
            document_metadata = metadata.get('document_metadata', {})
            if isinstance(document_metadata, dict):
                doc_id = document_metadata.get('document_id')
                if doc_id and doc_id in document_ids:
                    return True
            logging.debug(f"Document metadata check failed for {metadata}")
            return False
        
        # Apply document filtering
        filtered_df = results_df.copy()
        document_mask = filtered_df['metadata'].apply(matches_document)
        filtered_df = filtered_df[document_mask]
        
        logging.info(f"Post-search document filtering: {len(results_df)} -> {len(filtered_df)} results")
        
        return filtered_df


# Register this strategy with the factory
SearchStrategyFactory.register_strategy("HYBRID_KEYWORD_FALLBACK", HybridKeywordFallbackStrategy)
