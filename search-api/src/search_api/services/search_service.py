"""Service for search management."""
from .vector_search import search


class SearchService:
    """Search management service."""

    @classmethod
    def get_documents_by_question(cls, _question):
        """Get documents by question."""
        documents = search(_question)
        return {"documents": documents}

   