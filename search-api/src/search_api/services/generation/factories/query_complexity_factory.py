"""Factory for creating query complexity analyzer instances."""

import os
from typing import Type
from ..abstractions.query_complexity_analyzer import QueryComplexityAnalyzer


class QueryComplexityFactory:
    """Factory for creating query complexity analyzer instances based on configuration."""
    
    @staticmethod
    def create_analyzer() -> QueryComplexityAnalyzer:
        """Create and return a query complexity analyzer instance based on configuration.
        
        Returns:
            QueryComplexityAnalyzer: An instance of the configured query complexity analyzer.
            
        Raises:
            ValueError: If the provider is not supported or configuration is missing.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            from ..implementations.openai.openai_query_complexity_analyzer import OpenAIQueryComplexityAnalyzer
            return OpenAIQueryComplexityAnalyzer()
        elif provider == "ollama":
            from ..implementations.ollama.ollama_query_complexity_analyzer import OllamaQueryComplexityAnalyzer
            return OllamaQueryComplexityAnalyzer()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, ollama")
    
    @staticmethod
    def get_provider() -> str:
        """Get the current provider name."""
        return os.environ.get("LLM_PROVIDER", "openai").lower()