"""Document Only search strategy implementation.

This strategy implements direct document-level search without chunk analysis,
optimized for document browsing and metadata-based queries.
"""

import logging
import time
from typing import Tuple, List, Optional, Dict, Any

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory


class DocumentOnlyStrategy(BaseSearchStrategy):
    """Document-only search strategy that returns document-level results without chunk analysis.
    
    This strategy is designed for generic document requests where users want to browse
    documents of a specific type without searching for specific content within them.
    It performs direct metadata-based search and returns document-level information
    ordered by creation date or relevance.
    """
    
    @property
    def strategy_name(self) -> str:
        return "DOCUMENT_ONLY"
    
    @property
    def description(self) -> str:
        return ("Direct document-level search using metadata filtering without chunk analysis. "
                "Optimized for document browsing, generic requests, and scenarios where users "
                "want to see available documents rather than specific content matches.")
    
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
        """Execute the document only search strategy.
        
        Args:
            question (str): The search query (mainly for logging)
            vec_store: Vector store instance
            project_ids (list, optional): Project IDs for filtering
            document_type_ids (list, optional): Document type IDs for filtering
            doc_limit (int, optional): Maximum number of documents to return
            chunk_limit (int, optional): Not used in this strategy
            top_n (int, optional): Not used in this strategy
            min_relevance_score (float, optional): Not used in this strategy
            metrics (dict): Metrics dictionary to update
            start_time (float): Search start time
            
        Returns:
            tuple: (formatted_data, metrics)
        """
        # Import required functions from the main vector_search module
        from ..vector_search import (
            perform_direct_metadata_search,
            format_document_data
        )
        
        # Validate basic parameters (relaxed validation for document-only strategy)
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")
        
        if vec_store is None:
            raise ValueError("Vector store instance is required")
        
        # Initialize metrics if not provided
        if metrics is None:
            metrics = {}
        
        # Log strategy start
        self._log_strategy_start(question, project_ids, document_type_ids)
        logging.info("DOCUMENT_ONLY - Starting document-level search")
        logging.info(f"DOCUMENT_ONLY - Query: '{question}'")
        logging.info(f"DOCUMENT_ONLY - Project IDs: {project_ids}")
        logging.info(f"DOCUMENT_ONLY - Document Type IDs: {document_type_ids}")
        
        # Perform direct metadata search
        documents, metadata_search_time = perform_direct_metadata_search(
            vec_store, project_ids, document_type_ids, doc_limit
        )
        
        metrics["metadata_search_ms"] = metadata_search_time
        
        document_count = len(documents) if not documents.empty else 0
        logging.info(f"DOCUMENT_ONLY - Found {document_count} documents")
        
        # Format the document results directly (no re-ranking needed for date-ordered results)
        format_start = time.time()
        formatted_data = format_document_data(documents)
        metrics["formatting_ms"] = self._calculate_elapsed_time(format_start)
        
        # Total time
        if start_time is not None:
            metrics["total_search_ms"] = self._calculate_elapsed_time(start_time)
        metrics["search_mode"] = "document_only"
        
        # Log completion
        self._log_strategy_completion(len(formatted_data))
        
        return formatted_data, metrics


# Register this strategy with the factory
SearchStrategyFactory.register_strategy("DOCUMENT_ONLY", DocumentOnlyStrategy)
