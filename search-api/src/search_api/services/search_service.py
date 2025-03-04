"""Service for search management."""

from search_api.services.synthesizer import generate_response
from .vector_search import search


class SearchService:
    """Search management service."""

    @classmethod
    def get_documents_by_question(cls, _question):
        """Get documents by question."""
        documents = search(_question)
        response = generate_response(_question, documents)
        return {"result": response}
