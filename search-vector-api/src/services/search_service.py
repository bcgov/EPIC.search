"""Search service facade for accessing vector and keyword search functionality.

This service module provides a high-level interface for search operations,
abstracting th            if inferred_project_ids and project_confidence > 0.8:
                project_ids = inferred_project_ids
                # Only clean the query if it's NOT a generic request (to preserve generic patterns)
                if not is_generic_request:
                    project_cleaned_query = project_inference_service.clean_query_after_inference(cleaned_query, project_inference_metadata)
                    cleaned_query = project_cleaned_query
                logging.info(f"Project inference successful: Using inferred projects {inferred_project_ids} with confidence {project_confidence:.3f}")
                logging.info(f"Query after project cleaning: '{cleaned_query}'")exity of the underlying search implementation. It acts as a 
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
from .inference import InferencePipeline

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
    def get_documents_by_query(cls, query: str, project_ids: List[str] = None, document_type_ids: List[str] = None, inference: List[str] = None) -> Dict[str, Any]:
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
        - Detailed performance metrics for each stage of the pipeline
        - Consistent result formatting for API consumption
        
        Document Type Population:
        - All search results include a 'document_type' field with human-readable type names
        - For chunk-based results, the system prioritizes document type from chunk metadata:
          1. First checks chunk_metadata.document_metadata.document_type (preferred nested structure)
          2. Falls back to chunk_metadata.document_type (legacy direct field)
          3. If not found, looks up document_type_id from document-level metadata
          4. Uses the DOCUMENT_TYPE_LOOKUP to convert IDs to display names
        
        Inference Control:
        - The inference parameter controls which inference pipelines to run:
          * ['PROJECT'] - Only run project inference
          * ['DOCUMENTTYPE'] - Only run document type inference  
          * ['PROJECT', 'DOCUMENTTYPE'] - Run both inference pipelines
          * [] or None - Behavior depends on USE_DEFAULT_INFERENCE environment variable
        - When USE_DEFAULT_INFERENCE is True (default) and inference is not provided,
          both PROJECT and DOCUMENTTYPE inference will run
        - When USE_DEFAULT_INFERENCE is False and inference is not provided or empty,
          no inference pipelines will run
        - IMPORTANT: Inference is automatically skipped when explicit IDs are provided:
          * If project_ids are provided, PROJECT inference is skipped regardless of settings
          * If document_type_ids are provided, DOCUMENTTYPE inference is skipped regardless of settings
          * This prevents unnecessary processing when IDs are already known
        
        Args:
            query (str): The natural language search query
            project_ids (List[str], optional): Explicit project IDs to filter results.
                                             If None/empty and PROJECT inference is enabled,
                                             will attempt to infer project IDs from query.
            document_type_ids (List[str], optional): Explicit document type IDs to filter results.
                                                   If None/empty and DOCUMENTTYPE inference is enabled,
                                                   will attempt to infer document type IDs from query.
            inference (List[str], optional): List of inference types to run.
                                           Valid values: 'PROJECT', 'DOCUMENTTYPE'.
                                           If not provided, uses USE_DEFAULT_INFERENCE setting.
        
        Returns:
            Dict[str, Any]: Search results including documents and detailed metrics
        
        Examples:
            Search with explicit project and document type filtering:
            >>> SearchService.get_documents_by_query("water quality", ["proj-001"], ["5df79dd77b5abbf7da6f51be"])
            
            Search with automatic project and document type inference:
            >>> SearchService.get_documents_by_query("I am looking for the Inspection Record for the BC Hydro project")
            # System automatically infers BC Hydro project and Inspection Record document type
            
            Search with only project inference enabled:
            >>> SearchService.get_documents_by_query("correspondence", inference=["PROJECT"])
            # Only project inference will run, document type inference is skipped
            
            Search with inference disabled:
            >>> SearchService.get_documents_by_query("correspondence", inference=[])
            # No inference pipelines will run regardless of USE_DEFAULT_INFERENCE setting
            
            Search with explicit IDs (inference automatically skipped):
            >>> SearchService.get_documents_by_query("documents", project_ids=["proj-123"], document_type_ids=["type-456"], inference=["PROJECT", "DOCUMENTTYPE"])
            # Even though inference is enabled, it will be skipped because explicit IDs are provided
        """
        
        # Store original inputs for metadata
        original_project_ids = project_ids
        original_document_type_ids = document_type_ids
        
        # Determine which inference pipelines to run based on the inference parameter and environment setting
        from flask import current_app
        use_default_inference = current_app.search_settings.use_default_inference
        
        # Logic for determining inference behavior:
        # 1. If inference parameter is explicitly provided (even if empty), use it
        # 2. If inference parameter is None and USE_DEFAULT_INFERENCE is True, run all inference
        # 3. If inference parameter is None and USE_DEFAULT_INFERENCE is False, run no inference
        if inference is not None:
            # Explicit inference parameter provided - use it exactly as specified
            run_project_inference = 'PROJECT' in inference
            run_document_type_inference = 'DOCUMENTTYPE' in inference
            logging.info(f"Using explicit inference parameter: {inference}")
        elif use_default_inference:
            # No inference parameter provided and default inference is enabled - run all
            run_project_inference = True
            run_document_type_inference = True
            logging.info("Using default inference: PROJECT and DOCUMENTTYPE enabled")
        else:
            # No inference parameter provided and default inference is disabled - run none
            run_project_inference = False
            run_document_type_inference = False
            logging.info("Default inference disabled: no inference will run")
        
        # Use the inference pipeline for intelligent context detection
        pipeline = InferencePipeline()
        
        # Check if this is a generic document request for cleaning decisions
        from src.services.vector_search import is_generic_document_request
        is_generic_request = is_generic_document_request(query)
        
        # Process query through inference pipeline with controlled inference options
        inference_results = pipeline.process_query(
            query=query,
            project_ids=project_ids,
            document_type_ids=document_type_ids,
            skip_generic_cleaning=is_generic_request,
            run_project_inference=run_project_inference,
            run_document_type_inference=run_document_type_inference
        )
        
        # Extract results from pipeline
        search_query = inference_results["query_processing"]["final_query"]
        
        # Use inferred IDs if inference was successful
        if inference_results["project_inference"]["applied"]:
            project_ids = inference_results["project_inference"]["inferred_project_ids"]
            
        if inference_results["document_type_inference"]["applied"]:
            document_type_ids = inference_results["document_type_inference"]["inferred_document_type_ids"]
        
        # Debug logging to see what IDs are being passed
        logging.info(f"About to call search with: project_ids={project_ids}, document_type_ids={document_type_ids}, is_generic={is_generic_request}")
        
        # Use original query for generic requests, processed query for specific content searches
        final_search_query = query if is_generic_request else search_query
        logging.info(f"Using search query: '{final_search_query}' (is_generic: {is_generic_request})")
        
        documents, search_metrics = search(final_search_query, project_ids, document_type_ids)

        # Check if results have low confidence (indicating possible query-document mismatch)
        search_quality = "normal"
        search_note = None
        
        if documents:
            # Check if any document has low confidence flag
            has_low_confidence = any(doc.get("search_quality") == "low_confidence" for doc in documents)
            if has_low_confidence:
                search_quality = "low_confidence"
                search_note = "The query may not be well-matched to the available documents. Consider refining your search terms or using more specific keywords related to the document content."

        # Determine the appropriate key name based on search mode
        search_mode = search_metrics.get("search_mode", "semantic")
        if search_mode == "direct_metadata":
            # Document-level results from direct metadata search
            results_key = "documents"
        else:
            # Chunk-level results from semantic search
            results_key = "document_chunks"

        response = {
            "vector_search": {
                results_key: documents,                
                "search_metrics": search_metrics,
                "search_quality": search_quality,
                "original_query": query,
                "final_semantic_query": final_search_query,  # Show the actual query sent to vector search
                "search_mode": search_mode,
                "query_processed": inference_results["query_processing"]["query_changed"],  # Indicates if query was modified through cleaning
                "inference_settings": {
                    "use_default_inference": use_default_inference,
                    "inference_parameter": inference,
                    "project_inference_enabled": run_project_inference,
                    "document_type_inference_enabled": run_document_type_inference,
                    "project_inference_skipped": original_project_ids is not None and len(original_project_ids) > 0,
                    "document_type_inference_skipped": original_document_type_ids is not None and len(original_document_type_ids) > 0,
                    "skip_reason": "explicit_ids_provided" if (original_project_ids or original_document_type_ids) else None
                }
            }
        }
        
        if search_note:
            response["vector_search"]["search_note"] = search_note
        
        # Add project inference metadata if inference was attempted
        if not original_project_ids and inference_results["project_inference"]["attempted"]:
            response["vector_search"]["project_inference"] = {
                "attempted": True,
                "confidence": inference_results["project_inference"]["confidence"],
                "inferred_project_ids": inference_results["project_inference"]["inferred_project_ids"],
                "applied": inference_results["project_inference"]["applied"],
                "original_query": query,
                "cleaned_query": inference_results["project_inference"]["cleaned_query"],
                "metadata": inference_results["project_inference"]["metadata"]
            }
        
        # Add document type inference metadata if inference was attempted  
        if not original_document_type_ids and inference_results["document_type_inference"]["attempted"]:
            response["vector_search"]["document_type_inference"] = {
                "attempted": True,
                "confidence": inference_results["document_type_inference"]["confidence"],
                "inferred_document_type_ids": inference_results["document_type_inference"]["inferred_document_type_ids"],
                "applied": inference_results["document_type_inference"]["applied"],
                "original_query": inference_results["project_inference"]["cleaned_query"] or query,  # Show what query was actually used for doc type inference
                "cleaned_query": inference_results["document_type_inference"]["cleaned_query"],
                "metadata": inference_results["document_type_inference"]["metadata"]
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
