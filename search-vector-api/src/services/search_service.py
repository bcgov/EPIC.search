"""Service for search management."""

from .vector_search import search


class SearchService:
    """Search management service."""

    @classmethod
    def get_documents_by_query(cls, query):
        """Get documents by user query."""

        documents, search_metrics = search(query)  # Unpack the tuple

        return {
            "vector_search": {
                "documents": documents,                
                "search_metrics": search_metrics,
            }
        }
