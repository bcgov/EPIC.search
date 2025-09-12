"""Factory for creating LLM client instances."""

import os
from typing import Type
from ..abstractions.llm_client import LLMClient


class LLMClientFactory:
    """Factory for creating LLM client instances based on configuration."""
    
    @staticmethod
    def create_client() -> LLMClient:
        """Create and return an LLM client instance based on configuration.
        
        Returns:
            LLMClient: An instance of the configured LLM client.
            
        Raises:
            ValueError: If the provider is not supported or configuration is missing.
        """
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            from ..implementations.openai.openai_client import OpenAIClient
            return OpenAIClient()
        elif provider == "ollama":
            from ..implementations.ollama.ollama_client import OllamaClient
            return OllamaClient()
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}. Supported: openai, ollama")
    
    @staticmethod
    def get_provider() -> str:
        """Get the current provider name."""
        return os.environ.get("LLM_PROVIDER", "openai").lower()
    
    @staticmethod
    def is_openai() -> bool:
        """Check if the current provider is OpenAI."""
        return LLMClientFactory.get_provider() == "openai"
    
    @staticmethod
    def is_ollama() -> bool:
        """Check if the current provider is Ollama."""
        return LLMClientFactory.get_provider() == "ollama"