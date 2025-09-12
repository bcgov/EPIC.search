"""Factory for creating parameter extractor instances."""

import os
from typing import Type
from ..abstractions.parameter_extractor import ParameterExtractor


class ParameterExtractorFactory:
    """Factory for creating parameter extractor instances based on configuration."""
    
    @staticmethod
    def create_extractor() -> ParameterExtractor:
        """Create and return a parameter extractor instance based on configuration.
        
        Returns:
            ParameterExtractor: An instance of the configured parameter extractor.
            
        Raises:
            ValueError: If the provider is not supported or configuration is missing.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            from ..implementations.openai.openai_parameter_extractor import OpenAIParameterExtractor
            from ..factories.llm_factory import LLMClientFactory
            llm_client = LLMClientFactory.create_client()
            return OpenAIParameterExtractor(llm_client)
        elif provider == "ollama":
            from ..implementations.ollama.ollama_parameter_extractor import OllamaParameterExtractor
            from ..factories.llm_factory import LLMClientFactory
            llm_client = LLMClientFactory.create_client()
            return OllamaParameterExtractor(llm_client)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, ollama")
    
    @staticmethod
    def get_provider() -> str:
        """Get the current provider name."""
        return os.environ.get("LLM_PROVIDER", "openai").lower()