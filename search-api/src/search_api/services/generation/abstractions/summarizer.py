"""Abstract base class for summarizers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Summarizer(ABC):
    """Abstract base class for LLM summarizers."""
    
    @abstractmethod
    def summarize_search_results(self, query: str, documents_or_chunks: List[Dict[str, Any]],
                               search_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Summarize search results using LLM.
        
        Args:
            query: Original search query
            documents_or_chunks: List of document/chunk dictionaries
            search_context: Additional context about the search
            
        Returns:
            Dict containing summarization result:
            {
                'summary': str,
                'method': str,
                'confidence': float,
                'documents_count': int,
                'provider': str,
                'model': str
            }
        """
        pass