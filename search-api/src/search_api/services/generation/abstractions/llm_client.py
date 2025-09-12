"""Abstract base class for LLM clients."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def chat_completions_create(self, model: str, messages: List[Dict[str, str]], 
                               temperature: float = 0.3, **kwargs) -> Any:
        """Create a chat completion.
        
        Args:
            model: The model name to use
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Temperature for response generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Chat completion response object
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name (e.g., 'openai', 'ollama')."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used."""
        pass