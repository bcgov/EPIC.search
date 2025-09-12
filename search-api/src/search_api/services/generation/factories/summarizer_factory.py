"""Factory for creating summarizer instances."""

import os
from typing import Type
from ..abstractions.summarizer import Summarizer


class SummarizerFactory:
    """Factory for creating summarizer instances based on configuration."""
    
    @staticmethod
    def create_summarizer() -> Summarizer:
        """Create and return a summarizer instance based on configuration.
        
        Returns:
            Summarizer: An instance of the configured summarizer.
            
        Raises:
            ValueError: If the provider is not supported or configuration is missing.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            from ..implementations.openai.openai_summarizer import OpenAISummarizer
            return OpenAISummarizer()
        elif provider == "ollama":
            from ..implementations.ollama.ollama_summarizer import OllamaSummarizer
            return OllamaSummarizer()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, ollama")
    
    @staticmethod
    def get_provider() -> str:
        """Get the current provider name."""
        return os.environ.get("LLM_PROVIDER", "openai").lower()