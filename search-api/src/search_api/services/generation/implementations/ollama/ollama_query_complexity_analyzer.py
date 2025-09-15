"""Ollama implementation of query complexity analyzer."""

import os
import logging
from typing import List, Dict, Any
from ..base_query_complexity_analyzer import BaseQueryComplexityAnalyzer
from .ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class OllamaQueryComplexityAnalyzer(BaseQueryComplexityAnalyzer):
    """Ollama implementation of query complexity analyzer."""
    
    def __init__(self):
        """Initialize Ollama complexity analyzer."""
        self.client = OllamaClient()
    
    def _make_llm_call(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Dict[str, Any]:
        """Make Ollama API call."""
        try:
            response = self.client.chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=200  # Small response needed
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Ollama complexity analysis call failed: {e}")
            raise