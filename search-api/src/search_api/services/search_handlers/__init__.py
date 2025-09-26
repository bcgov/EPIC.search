"""
Search Handlers Package

This package contains specialized handlers for different search modes:
- RAGHandler: Basic RAG mode with pattern-based temporal extraction
- RAGSummaryHandler: RAG + AI summarization with pattern-based temporal extraction  
- AIHandler: LLM parameter extraction + AI summarization
- AgentHandler: Autonomous agent mode with multi-step processing

Each handler implements the BaseSearchHandler interface for consistent behavior.
"""

from .base_handler import BaseSearchHandler
from .rag_handler import RAGHandler
from .rag_summary_handler import RAGSummaryHandler
from .ai_handler import AIHandler
from .agent_handler import AgentHandler

__all__ = [
    'BaseSearchHandler',
    'RAGHandler',
    'RAGSummaryHandler', 
    'AIHandler',
    'AgentHandler'
]