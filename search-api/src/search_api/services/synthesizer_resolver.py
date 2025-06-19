"""Factory module for resolving and instantiating LLM synthesizer implementations.

This module provides a factory function to create the appropriate LLM synthesizer
instance based on the current configuration. It supports extensibility by allowing
new synthesizer implementations to be added and resolved.
"""

import os
from search_api.services.generation.llm_synthesizer import LLMSynthesizer
from search_api.services.generation.openai.azure_openai_synthesizer import AzureOpenAISynthesizer
from search_api.services.generation.ollama.ollama_synthesizer import OllamaSynthesizer


def get_synthesizer() -> LLMSynthesizer:
    """Create and return an instance of the configured LLM synthesizer.
    
    This factory function returns either an AzureOpenAISynthesizer or OllamaSynthesizer
    instance based on the LLM_PROVIDER environment variable.
    
    Returns:
        LLMSynthesizer: An instance of a class implementing the LLMSynthesizer interface.
        
    Note:
        To add support for additional synthesizer types:
        1. Create a new class implementing the LLMSynthesizer interface
        2. Import the new class
        3. Modify this function to return the appropriate instance based on configuration
    """      
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    
    if provider == "openai":
        return AzureOpenAISynthesizer()
    elif provider == "ollama":
        return OllamaSynthesizer()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")