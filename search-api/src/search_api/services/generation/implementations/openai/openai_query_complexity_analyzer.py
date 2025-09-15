"""OpenAI implementation of query complexity analyzer."""

import os
import logging
from typing import List, Dict, Any
from ..base_query_complexity_analyzer import BaseQueryComplexityAnalyzer
from .openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class OpenAIQueryComplexityAnalyzer(BaseQueryComplexityAnalyzer):
    """OpenAI implementation of query complexity analyzer."""
    
    def __init__(self):
        """Initialize OpenAI complexity analyzer."""
        self.client = OpenAIClient()
    
    def _make_llm_call(self, messages: List[Dict[str, str]], temperature: float = 0.1) -> Dict[str, Any]:
        """Make OpenAI API call."""
        try:
            response = self.client.chat_completions_create(
                model="gpt-4o-mini",  # Model name (will use configured deployment)
                messages=messages,
                temperature=temperature,
                max_tokens=200  # Small response needed
            )
            
            return response
            
        except Exception as e:
            logger.error(f"OpenAI complexity analysis call failed: {e}")
            raise