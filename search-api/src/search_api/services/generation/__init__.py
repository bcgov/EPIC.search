"""Generation services package with abstraction-based architecture.

This package provides LLM-based services for parameter extraction, document summarization,
and response generation. It supports multiple providers (OpenAI, Ollama) through a 
factory pattern with abstract base classes.

Usage:
    from search_api.services.generation.factories import (
        LLMClientFactory, 
        ParameterExtractorFactory, 
        SummarizerFactory
    )
    
    # Create instances based on environment configuration
    llm_client = LLMClientFactory.create_client()
    parameter_extractor = ParameterExtractorFactory.create_extractor()
    summarizer = SummarizerFactory.create_summarizer()
"""

from .factories import LLMClientFactory, ParameterExtractorFactory, SummarizerFactory

__all__ = [
    "LLMClientFactory",
    "ParameterExtractorFactory",
    "SummarizerFactory"
]