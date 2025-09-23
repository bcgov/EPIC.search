"""Abstract base class for query complexity analysis."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class QueryComplexityAnalyzer(ABC):
    """Abstract base class for analyzing query complexity and determining search approach."""
    
    @abstractmethod
    def analyze_complexity(self, query: str, project_ids: Optional[List[str]] = None, 
                         document_type_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze query complexity and determine search approach.
        
        Args:
            query: The natural language search query.
            project_ids: Optional list of project IDs already selected in UI.
            document_type_ids: Optional list of document type IDs already selected in UI.
            
        Returns:
            Dict containing:
            - complexity_tier: str ("simple", "complex", "agent_required")
            - reason: str (explanation for the decision)
            - confidence: float (0.0 to 1.0)
        """
        pass