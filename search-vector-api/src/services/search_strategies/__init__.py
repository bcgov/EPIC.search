"""Search strategies module for the vector search system.

This module provides a modular approach to implementing different search strategies,
each with their own specific behavior and optimization characteristics.

Available Strategies:
- HYBRID_SEMANTIC_FALLBACK: Document filtering → semantic search → keyword fallback (default)
- HYBRID_KEYWORD_FALLBACK: Document filtering → keyword search → semantic fallback  
- SEMANTIC_ONLY: Pure semantic search across all chunks
- KEYWORD_ONLY: Pure keyword search across all chunks
- HYBRID_PARALLEL: Parallel semantic and keyword search with result merging
- DOCUMENT_ONLY: Direct document metadata search without chunk-level search

Usage:
    from .search_strategies import get_search_strategy
    
    strategy = get_search_strategy("HYBRID_SEMANTIC_FALLBACK")
    results, metrics = strategy.execute(question, vec_store, ...)
"""

from .base_strategy import BaseSearchStrategy
from .strategy_factory import SearchStrategyFactory, get_search_strategy, list_available_strategies

# Import all strategy implementations to ensure they're registered
from . import hybrid_semantic_fallback
from . import hybrid_keyword_fallback  
from . import semantic_only
from . import keyword_only
from . import hybrid_parallel
from . import document_only

__all__ = [
    'BaseSearchStrategy',
    'SearchStrategyFactory', 
    'get_search_strategy',
    'list_available_strategies'
]
