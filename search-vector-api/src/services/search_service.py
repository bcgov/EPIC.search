"""Search service facade for accessing vector and keyword search functionality.

This service module provides a high-level interface for search operations,
abstracting the complexity of the underlying search implementation. It acts as a 
facade between the API layer and the core search engine components, providing:

1. A clean, simplified interface for the REST API endpoints
2. Consistent result formatting and structure
3. A single entry point for search operations
4. Abstraction of the multi-stage search pipeline details

The service delegates the actual search operations to specialized components
while maintaining a consistent API for clients.
"""

from typing import Dict, List, Any

from .vector_search import search

class SearchService:
    """Search management service for document retrieval and ranking.
    
    This service class provides a simplified interface for searching documents
    using a combination of semantic vector similarity and keyword-based search.
    It encapsulates the complete search pipeline and formats results consistently.
    
    The class follows a facade design pattern, providing a unified interface
    to the complex subsystem of search operations without exposing the
    underlying implementation details.
    """

    @classmethod
    def get_documents_by_query(cls, query: str) -> Dict[str, Any]:
        """Retrieve relevant documents matching the provided query text.
        
        Processes the user's natural language query and returns the most relevant
        documents by executing the complete search pipeline:
        1. Performing parallel keyword and semantic vector searches
        2. Combining and deduplicating results
        3. Re-ranking documents for optimal relevance ordering
        4. Formatting results for API consumption
        5. Collecting performance metrics for each stage
        
        Args:
            query (str): The natural language search query text
            
        Returns:
            dict: A structured response containing search results and detailed metrics:
                {
                    "vector_search": {
                        "documents": [
                            {
                                "document_id": "uuid",
                                "document_type": "type",
                                "document_name": "name",
                                "document_saved_name": "filename",
                                "page_number": 1,
                                "project_id": "project-uuid",
                                "project_name": "Project Name",
                                "proponent_name": "Proponent Name",
                                "content": "Document content extract..."
                            },
                            ...
                        ],
                        "search_metrics": {
                            "keyword_search_ms": 52.15,
                            "semantic_search_ms": 157.89,
                            "combine_results_ms": 1.23,
                            "deduplication_ms": 0.98,
                            "reranking_ms": 235.67,
                            "formatting_ms": 3.45,
                            "total_search_ms": 451.37
                        }
                    }
                }
        """

        documents, search_metrics = search(query)  # Unpack the tuple

        return {
            "vector_search": {
                "documents": documents,                
                "search_metrics": search_metrics,
            }
        }
