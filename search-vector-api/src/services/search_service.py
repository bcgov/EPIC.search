"""Service for vector and keyword search operations.

This service provides high-level search functionality that combines vector-based 
semantic search with keyword-based search capabilities. It handles the orchestration
of search operations, result processing, and format standardization.
"""

from .vector_search import search

class SearchService:
    """Search management service for document retrieval.
    
    This service class provides methods for searching documents using semantic 
    vector similarity and keyword-based search. It acts as a facade to the 
    underlying search implementation.
    """

    @classmethod
    def get_documents_by_query(cls, query):
        """Get documents by user query using vector and keyword search.
        
        This method processes the user's query text and returns relevant documents
        by performing semantic and/or keyword search. Results are ranked by 
        relevance using a cross-encoder model.
        
        Args:
            query (str): The search query text
            
        Returns:
            dict: A dictionary containing search results and metrics with the structure:
                {
                    "vector_search": {
                        "documents": [list of document objects],
                        "search_metrics": {search performance metrics}
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
