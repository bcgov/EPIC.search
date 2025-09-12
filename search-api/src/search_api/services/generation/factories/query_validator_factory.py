"""Factory for creating query validator instances."""

import os
from typing import Type
from ..abstractions.query_validator import QueryValidator


class QueryValidatorFactory:
    """Factory for creating query validator instances based on configuration."""
    
    @staticmethod
    def create_validator() -> QueryValidator:
        """Create and return a query validator instance based on configuration.
        
        Returns:
            QueryValidator: An instance of the configured query validator.
            
        Raises:
            ValueError: If the provider is not supported or configuration is missing.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            from ..implementations.openai.openai_query_validator import OpenAIQueryValidator
            return OpenAIQueryValidator()
        elif provider == "ollama":
            from ..implementations.ollama.ollama_query_validator import OllamaQueryValidator
            return OllamaQueryValidator()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, ollama")
    
    @staticmethod
    def get_provider() -> str:
        """Get the current provider name."""
        return os.environ.get("LLM_PROVIDER", "openai").lower()