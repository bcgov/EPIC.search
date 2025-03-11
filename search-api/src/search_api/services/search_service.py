"""Service for search management."""

from search_api.services.synthesizer import generate_response, validate_question
from .vector_search import search


class SearchService:
    """Search management service."""

    @classmethod
    def get_documents_by_question(cls, _question):
        """Get documents by question."""
        query_validation = validate_question(_question)

        if "Not Relevant" in query_validation["response"]:
            return {
                "result": {
                    "response": "Sorry, I can't assist you with that.",
                    "documents": [],
                },                
            }

        documents = search(_question)
        response = generate_response(_question, documents)
        
        return {
            "result": {
                "response": response["response"],
                "documents": response["documents"],
            },            
        }
