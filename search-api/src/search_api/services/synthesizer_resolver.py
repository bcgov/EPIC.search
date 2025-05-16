"""Factory module for resolving and instantiating LLM synthesizer implementations.

This module provides a factory function to create the appropriate LLM synthesizer
instance based on the current configuration. It supports extensibility by allowing
new synthesizer implementations to be added and resolved.
"""

from search_api.services.generation.llm_synthesizer import LLMSynthesizer
from search_api.services.generation.ollama.ollama_synthesizer import OllamaSynthesizer


def get_synthesizer() -> LLMSynthesizer:
    """Create and return an instance of the configured LLM synthesizer.
    
    This factory function currently returns an OllamaSynthesizer instance by default.
    The function can be extended to support different synthesizer implementations
    based on configuration or environment settings.
    
    Returns:
        LLMSynthesizer: An instance of a class implementing the LLMSynthesizer interface.
        Currently returns an OllamaSynthesizer instance.
        
    Note:
        To add support for additional synthesizer types:
        1. Create a new class implementing the LLMSynthesizer interface
        2. Import the new class
        3. Modify this function to return the appropriate instance based on configuration
    """
    return OllamaSynthesizer()