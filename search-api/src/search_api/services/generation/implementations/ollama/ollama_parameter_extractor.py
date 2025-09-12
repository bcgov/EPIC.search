"""
Ollama Parameter Extractor Implementation
Breaks parameter extraction into focused, sequential calls for better accuracy.
"""
import logging
from typing import Dict, List, Any

from search_api.services.generation.implementations.base_parameter_extractor import BaseParameterExtractor

logger = logging.getLogger(__name__)

class OllamaParameterExtractor(BaseParameterExtractor):
    """Ollama implementation of parameter extractor."""
    
    def _make_llm_call(self, messages: List[Dict], temperature: float = 0.1) -> Dict[str, Any]:
        """Make Ollama chat completion call."""
        return self.client.chat_completion(
            messages=messages,
            temperature=temperature
        )