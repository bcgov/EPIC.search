"""Base strategy class for search implementations.

This module provides the abstract base class that all search strategies must inherit from,
ensuring a consistent interface and shared functionality across all strategy implementations.
"""

from abc import ABC, abstractmethod
import time
import logging
from typing import Tuple, List, Optional, Dict, Any
import pandas as pd


class BaseSearchStrategy(ABC):
    """Abstract base class for all search strategies.
    
    This class defines the standard interface that all search strategies must implement,
    ensuring consistency in how strategies are executed and results are returned.
    """
    
    @abstractmethod
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
        """Execute the search strategy and return results and metrics.
        
        Args:
            question (str): The search query text
            vec_store: Vector store instance for performing searches
            project_ids (list, optional): List of project IDs to filter results
            document_type_ids (list, optional): List of document type IDs to filter results
            doc_limit (int, optional): Maximum number of documents to retrieve in document-level search
            chunk_limit (int, optional): Maximum number of chunks to retrieve in chunk-level search
            top_n (int, optional): Final number of results to return after re-ranking
            min_relevance_score (float, optional): Minimum relevance score threshold
            metrics (dict): Metrics dictionary to update with strategy-specific metrics
            start_time (float): Strategy execution start time for total timing
            semantic_query (str, optional): Pre-optimized semantic query for vector search. If provided,
                                          strategies should use this instead of the original question for
                                          semantic/vector operations while still using question for logging.
            
        Returns:
            tuple: A tuple containing:
                - list: Formatted search results as a list of dictionaries
                - dict: Updated metrics dictionary with timing and strategy information
        """
        pass
    
    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the strategy name for identification and logging."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a human-readable description of what this strategy does."""
        pass
    
    def _update_metrics(self, metrics: Dict[str, Any], **kwargs) -> None:
        """Helper method to update metrics dictionary with strategy-specific data.
        
        Args:
            metrics (dict): The metrics dictionary to update
            **kwargs: Key-value pairs to add to metrics
        """
        if metrics is not None:
            metrics.update(kwargs)
    
    def _calculate_elapsed_time(self, start_time: float) -> float:
        """Helper method to calculate elapsed time in milliseconds.
        
        Args:
            start_time (float): The start time from time.time()
            
        Returns:
            float: Elapsed time in milliseconds, rounded to 2 decimal places
        """
        return round((time.time() - start_time) * 1000, 2)
    
    def _log_strategy_start(self, question: str, project_ids: Optional[List[str]], 
                           document_type_ids: Optional[List[str]]) -> None:
        """Helper method to log strategy execution start.
        
        Args:
            question (str): The search query
            project_ids (list, optional): Project IDs filter
            document_type_ids (list, optional): Document type IDs filter
        """
        logging.info(f"{self.strategy_name} - Starting search for query: '{question}'")
        logging.info(f"{self.strategy_name} - Project IDs: {project_ids}, Document Type IDs: {document_type_ids}")
    
    def _log_strategy_completion(self, result_count: int) -> None:
        """Helper method to log strategy execution completion.
        
        Args:
            result_count (int): Number of final results returned
        """
        logging.info(f"{self.strategy_name} - Completed: {result_count} final results")
    
    def _validate_parameters(
        self, 
        question: str, 
        vec_store, 
        top_n: Optional[int], 
        min_relevance_score: Optional[float]
    ) -> None:
        """Validate common strategy parameters.
        
        Args:
            question (str): The search query text
            vec_store: Vector store instance
            top_n (int, optional): Final result count
            min_relevance_score (float, optional): Minimum relevance threshold
            
        Raises:
            ValueError: If any parameters are invalid
        """
        if not question or not isinstance(question, str):
            raise ValueError("Question must be a non-empty string")
        
        if vec_store is None:
            raise ValueError("Vector store instance is required")
        
        if top_n is not None and (not isinstance(top_n, int) or top_n <= 0):
            raise ValueError("top_n must be a positive integer")
        
        if min_relevance_score is not None and not isinstance(min_relevance_score, (int, float)):
            raise ValueError("min_relevance_score must be a number")
