"""Abstract base class for query complexity analysis."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class QueryComplexityAnalyzer(ABC):
    """Abstract base class for analyzing query complexity and determining search approach."""
    
    @abstractmethod
    def analyze_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity and determine search approach.
        
        Args:
            query: The natural language search query.
            
        Returns:
            Dict containing:
            - complexity_tier: str ("simple", "complex", "agent_required")
            - reason: str (explanation for the decision)
            - confidence: float (0.0 to 1.0)
        """
        pass