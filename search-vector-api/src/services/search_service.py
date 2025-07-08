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

import logging
from typing import Dict, List, Any

from .vector_search import search, document_similarity_search
from .project_inference import project_inference_service

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
    def get_documents_by_query(cls, query: str, project_ids: List[str] = None) -> Dict[str, Any]:
        """Retrieve relevant documents using an advanced two-stage search strategy with intelligent project inference.
        
        This method implements a modern search approach that leverages document-level
        metadata for improved efficiency and accuracy:
        
        Stage 0: Intelligent Project Inference (when no project_ids provided)
        - Analyzes the query for project names and project-related entities
        - Matches extracted entities against known projects using fuzzy matching
        - Automatically applies project filtering when confidence exceeds 80%
        - Removes identified project names from search terms to focus on actual topics
        - Only activates when no explicit project IDs are provided in the request
        
        Stage 1: Document Discovery
        - Searches the documents table using pre-computed keywords, tags, and headings
        - Applies project filtering (explicit or inferred) to narrow search scope
        - Identifies the most relevant documents based on metadata matching
        - Much faster than searching all chunks directly
        
        Stage 2: Chunk Retrieval
        - Performs semantic vector search within the chunks of relevant documents
        - Uses embeddings to find the most semantically similar content
        - Returns the best matching chunks from the promising documents
        
        Fallback Strategy:
        - If no relevant documents are found in Stage 1, falls back to searching all chunks
        - Ensures comprehensive coverage even for edge cases
        
        The pipeline also includes:
        - Cross-encoder re-ranking for optimal relevance ordering
        - Intelligent query-document mismatch detection
        - Detailed performance metrics for each stage
        - Consistent result formatting for API consumption
        
        Args:
            query (str): The natural language search query text
            project_ids (List[str], optional): List of project IDs to filter results.
                                             If None or empty, the system will attempt to
                                             infer relevant projects from the query text.
            
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
                                "content": "Document content extract...",
                                "relevance_score": 0.85,
                                "search_quality": "normal"  # or "low_confidence"
                            },
                            ...
                        ],
                        "search_metrics": {
                            "document_search_ms": 25.15,      # Stage 1: Document discovery
                            "chunk_search_ms": 89.42,         # Stage 2: Chunk retrieval
                            "reranking_ms": 156.78,           # Cross-encoder re-ranking
                            "formatting_ms": 2.34,            # Result formatting
                            "total_search_ms": 273.69         # Total pipeline time
                        },
                        "search_quality": "normal",           # Overall search quality assessment
                        "project_inference": {               # Present when inference attempted
                            "attempted": true,
                            "confidence": 0.95,
                            "inferred_project_ids": ["proj-001"],
                            "applied": true,
                            "metadata": {
                                "extracted_entities": ["BC Hydro"],
                                "matched_projects": [...],
                                "reasoning": [...]
                            }
                        }
                    }
                }
                
        Examples:
            Basic search across all projects:
            >>> SearchService.get_documents_by_query("environmental impact assessment")
            
            Search with explicit project filtering:
            >>> SearchService.get_documents_by_query("water quality", ["proj-001", "proj-002"])
            
            Search with automatic project inference:
            >>> SearchService.get_documents_by_query("who is the main proponent for the BC Hydro project?")
            # System automatically infers and applies BC Hydro project filtering
        """
        
        # Smart project inference: only when no explicit project IDs are provided
        inferred_project_ids = None
        inference_metadata = None
        confidence = 0.0
        original_project_ids = project_ids
        cleaned_query = query  # Default to original query
        
        if not project_ids:  # Only infer if no explicit project IDs provided
            inferred_project_ids, confidence, inference_metadata = project_inference_service.infer_projects_from_query(query)
            
            if inferred_project_ids and confidence > 0.8:  # High confidence threshold
                project_ids = inferred_project_ids
                # Clean the query to remove project names that were used for inference
                cleaned_query = project_inference_service.clean_query_after_inference(query, inference_metadata)
                logging.info(f"Project inference successful: Using inferred projects {inferred_project_ids} with confidence {confidence:.3f}")
                logging.info(f"Using cleaned query: '{cleaned_query}' (original: '{query}')")
            else:
                logging.info(f"Project inference skipped: confidence {confidence:.3f} below threshold or no projects found")
        
        documents, search_metrics = search(cleaned_query, project_ids)  # Use cleaned query for search

        # Check if results have low confidence (indicating possible query-document mismatch)
        search_quality = "normal"
        search_note = None
        
        if documents:
            # Check if any document has low confidence flag
            has_low_confidence = any(doc.get("search_quality") == "low_confidence" for doc in documents)
            if has_low_confidence:
                search_quality = "low_confidence"
                search_note = "The query may not be well-matched to the available documents. Consider refining your search terms or using more specific keywords related to the document content."

        response = {
            "vector_search": {
                "documents": documents,                
                "search_metrics": search_metrics,
                "search_quality": search_quality,
            }
        }
        
        if search_note:
            response["vector_search"]["search_note"] = search_note
        
        # Add project inference metadata if inference was attempted
        if not original_project_ids and inference_metadata:
            response["vector_search"]["project_inference"] = {
                "attempted": True,
                "confidence": confidence,
                "inferred_project_ids": inferred_project_ids or [],
                "applied": bool(inferred_project_ids and confidence > 0.8),
                "original_query": query,
                "cleaned_query": cleaned_query if cleaned_query != query else None,
                "metadata": inference_metadata
            }
            
        return response

    @classmethod
    def get_similar_documents(cls, document_id: str, project_ids: List[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Find documents similar to the specified document using document-level embeddings.
        
        This method retrieves the embedding for the specified document and performs
        cosine similarity search against other documents in the database. The search
        leverages document-level embeddings which represent the semantic content of
        the document's keywords, tags, and headings.
        
        The similarity search process:
        1. Retrieves the embedding vector for the source document
        2. Performs cosine similarity search against all other document embeddings
        3. Optionally filters results by project IDs
        4. Returns the most similar documents ranked by similarity score
        
        Args:
            document_id (str): The ID of the document to find similar documents for
            project_ids (List[str], optional): List of project IDs to filter results.
                                             If None or empty, searches across all projects.
            limit (int): Maximum number of similar documents to return (default: 10)
            
        Returns:
            dict: A structured response containing similar documents and search metrics:
                {
                    "document_similarity": {
                        "source_document_id": "doc-123",
                        "documents": [
                            {
                                "document_id": "similar-doc-456",
                                "document_keywords": [...],
                                "document_tags": [...],
                                "document_headings": [...],
                                "project_id": "project-789",
                                "similarity_score": 0.87,
                                "created_at": "2024-01-15T10:30:00Z"
                            },
                            ...
                        ],
                        "search_metrics": {
                            "embedding_retrieval_ms": 5.2,
                            "similarity_search_ms": 45.8,
                            "formatting_ms": 1.1,
                            "total_search_ms": 52.1
                        }
                    }
                }
        """
        
        similar_documents, search_metrics = document_similarity_search(document_id, project_ids, limit)
        
        return {
            "document_similarity": {
                "source_document_id": document_id,
                "documents": similar_documents,
                "search_metrics": search_metrics,
            }
        }
