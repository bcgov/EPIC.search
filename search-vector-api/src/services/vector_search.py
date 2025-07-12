"""Vector search implementation combining semantic and keyword search capabilities.

This module provides the core search functionality that combines semantic vector search
with keyword-based search. It implements the complete search pipeline including:

1. Performing keyword-based search using PostgreSQL full-text search
2. Performing semantic vector search using pgvector similarity matching
3. Combining results from both search methods
4. Removing duplicate results based on document ID
5. Re-ranking results using a cross-encoder model for improved relevance
6. Formatting results for the API response
7. Tracking performance metrics for each step of the pipeline

The search pipeline is designed to provide high-quality search results by leveraging
both traditional keyword matching and modern embedding-based semantic similarity.
"""

import pandas as pd
import time
from flask import current_app
from .bert_keyword_extractor import get_keywords
from .re_ranker import rerank_results, rerank_results_with_metrics
from .vector_store import VectorStore
import re


def get_document_type_name(document_metadata, chunk_metadata=None):
    """Map document type ID to document type name using available metadata.
    
    This function supports multiple metadata structures to ensure robust document type
    population across different data sources:
    
    Priority Order:
    1. chunk_metadata.document_metadata.document_type (preferred nested structure)
    2. chunk_metadata.document_type (legacy direct field for backward compatibility)
    3. document_metadata.documentType (document-level direct field)
    4. document_metadata.document_type_id (lookup via document type mapping)
    
    Args:
        document_metadata (dict): The document metadata containing document_type_id (from documents table)
        chunk_metadata (dict, optional): The chunk metadata that should contain a document_metadata object
                                        with document_type field, or a direct document_type field for legacy support
        
    Returns:
        str: The document type name/display name, or None if not found
    """
    # First try to get document type from chunk metadata's document_metadata object
    if chunk_metadata:
        # Check if chunk metadata contains a document_metadata object
        chunk_doc_metadata = chunk_metadata.get('document_metadata')
        if chunk_doc_metadata and isinstance(chunk_doc_metadata, dict):
            document_type = chunk_doc_metadata.get('document_type')
            if document_type:
                return document_type
        
        # Fallback: try direct document_type field (legacy support)
        direct_document_type = chunk_metadata.get('document_type')
        if direct_document_type:
            return direct_document_type
    
    # Then try to get document type from document_metadata (document-level results)
    if document_metadata:
        # First try the direct documentType field (most reliable)
        document_type = document_metadata.get('documentType')
        if document_type:
            return document_type
            
        # Fallback to lookup by document_type_id
        document_type_id = document_metadata.get('document_type_id')
        if document_type_id:
            try:
                # Import the document types lookup dictionary using absolute import
                from src.utils.document_types import DOCUMENT_TYPE_LOOKUP
                
                # Look up the document type name by ID
                document_type_name = DOCUMENT_TYPE_LOOKUP.get(document_type_id)
                
                if document_type_name:
                    return document_type_name
                    
            except ImportError:
                # Try alternative import paths
                try:
                    from utils.document_types import DOCUMENT_TYPE_LOOKUP
                    document_type_name = DOCUMENT_TYPE_LOOKUP.get(document_type_id)
                    if document_type_name:
                        return document_type_name
                except ImportError:
                    pass
            except Exception:
                pass
            
            # If lookup fails, return the ID as fallback
            return document_type_id
    
    # No document type found
    return None


def search(question, project_ids=None, document_type_ids=None):
    """Main search function implementing a two-stage search strategy.
    
    This function orchestrates a modern search pipeline that leverages document-level
    metadata for improved efficiency and accuracy:
    
    Direct Metadata Mode: When both project and document type are specified and the query
    is generic (e.g., "any correspondence"), returns document-level results ordered by date
    
    Stage 1: Document-level filtering using pre-computed keywords, tags, and headings
    Stage 2: Semantic search within relevant document chunks
    
    This approach is much more efficient than searching all chunks and provides
    better relevance by first identifying the most promising documents.
    
    Args:
        question (str): The search query text
        project_ids (list, optional): List of project IDs to filter results.
                                    If None or empty, searches across all projects.
        document_type_ids (list, optional): List of document type IDs to filter results.
                                          If None or empty, searches across all document types.
        
    Returns:
        tuple: A tuple containing:
            - list: Formatted search results as a list of dictionaries
            - dict: Search performance metrics in milliseconds for each search stage
    """
    metrics = {}
    start_time = time.time()
    
    # Use strongly typed configuration properties
    doc_limit = current_app.search_settings.keyword_fetch_count  # Number of documents to find
    chunk_limit = current_app.search_settings.semantic_fetch_count  # Number of chunks to return
    top_n = current_app.search_settings.top_record_count
    
    # Instantiate VectorStore
    vec_store = VectorStore()
    
    # Check if this should be a direct metadata search (generic document request)
    if (project_ids and document_type_ids and 
        is_generic_document_request(question)):
        
        import logging
        logging.info(f"Direct metadata search mode activated for query: '{question}'")
        logging.info(f"Project IDs: {project_ids}, Document Type IDs: {document_type_ids}")
        
        # Perform direct metadata search
        documents, metadata_search_time = perform_direct_metadata_search(
            vec_store, project_ids, document_type_ids, doc_limit
        )
        metrics["metadata_search_ms"] = metadata_search_time
        metrics["search_mode"] = "direct_metadata"
        
        # Format the document results directly (no re-ranking needed for date-ordered results)
        format_start = time.time()
        formatted_data = format_document_data(documents)
        metrics["formatting_ms"] = round((time.time() - format_start) * 1000, 2)
        
        # Total time
        metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
        
        logging.info(f"Direct metadata search completed: {len(formatted_data)} documents found")
        
        return formatted_data, metrics
    
    # Stage 1: Find relevant documents using document-level metadata
    relevant_documents, doc_search_time = perform_document_level_search(vec_store, question, doc_limit, project_ids, document_type_ids)
    metrics["document_search_ms"] = doc_search_time
    
    # Debug logging
    import logging
    logging.info(f"Stage 1 - Document search found {len(relevant_documents) if not relevant_documents.empty else 0} documents")
    
    # Stage 2: Search chunks within the relevant documents
    if not relevant_documents.empty:
        document_ids = relevant_documents["document_id"].tolist()
        chunk_results, chunk_search_time = perform_chunk_search_within_documents(
            vec_store, document_ids, question, chunk_limit
        )
        metrics["chunk_search_ms"] = chunk_search_time
    else:
        # Alternative path: if no documents found, perform semantic search across all chunks with project filtering
        logging.info("Stage 2 - No documents found, using semantic search across all chunks")
        chunk_results, semantic_search_time = perform_semantic_search_all_chunks(vec_store, question, chunk_limit, project_ids, document_type_ids)
        metrics["semantic_search_ms"] = semantic_search_time
        logging.info(f"Semantic search across all chunks found {len(chunk_results) if not chunk_results.empty else 0} chunks")
    
    # If both document search and semantic search returned no results, try a simple keyword search
    if chunk_results.empty:
        logging.info("Stage 2.5 - Semantic search returned no results, trying keyword search as last resort")
        try:
            table_name = current_app.vector_settings.vector_table_name
            keyword_results, keyword_time = perform_keyword_search(vec_store, table_name, question, chunk_limit)
            if not keyword_results.empty:
                chunk_results = keyword_results
                metrics["keyword_fallback_ms"] = keyword_time
                logging.info(f"Keyword fallback found {len(chunk_results)} chunks")
            else:
                logging.info("Keyword fallback also returned no results")
        except Exception as e:
            logging.error(f"Keyword fallback search failed: {e}")
    
    # Debug chunk_results before re-ranking
    logging.info(f"About to re-rank: chunk_results type={type(chunk_results)}, shape={chunk_results.shape if hasattr(chunk_results, 'shape') else 'no shape'}")
    if not chunk_results.empty:
        logging.info(f"chunk_results columns: {list(chunk_results.columns)}")
        logging.info(f"First chunk result sample: {chunk_results.iloc[0].to_dict()}")
    else:
        logging.warning("chunk_results is empty before re-ranking!")
    
    # Re-rank results using cross-encoder
    reranked_results, rerank_time, filtering_metrics = perform_reranking(question, chunk_results, top_n)
    metrics["reranking_ms"] = rerank_time
    
    # Add filtering metrics to the search metrics
    metrics.update({
        "filtering_total_chunks": filtering_metrics["total_chunks_before_filtering"],
        "filtering_excluded_chunks": filtering_metrics["excluded_chunks_count"],
        "filtering_exclusion_percentage": filtering_metrics["exclusion_percentage"],
        "filtering_final_chunks": filtering_metrics["final_chunk_count"]
    })
    
    # Add score range information if available
    if filtering_metrics["score_range_excluded"]:
        metrics["filtering_excluded_score_range"] = filtering_metrics["score_range_excluded"]
    if filtering_metrics["score_range_included"]:
        metrics["filtering_included_score_range"] = filtering_metrics["score_range_included"]
    
    results = reranked_results
    
    # Debug logging for re-ranking
    logging.info(f"Before re-ranking: {len(chunk_results)} chunks")
    logging.info(f"After re-ranking: {len(results)} results")
    logging.info(f"Re-ranked results type: {type(results)}")
    if hasattr(results, 'columns'):
        logging.info(f"Re-ranked results columns: {list(results.columns)}")
    if not results.empty:
        logging.info(f"Sample re-ranked result: {results.iloc[0].to_dict()}")
    else:
        logging.warning("Re-ranking returned empty DataFrame!")
    
    # Format the data
    format_start = time.time()
    formatted_data = format_data(results)
    metrics["formatting_ms"] = round((time.time() - format_start) * 1000, 2)
    
    # Debug logging for formatted data
    logging.info(f"Formatting completed. Formatted data length: {len(formatted_data)}")
    if formatted_data:
        logging.info(f"First formatted result keys: {list(formatted_data[0].keys())}")
        logging.info(f"Sample formatted result: {formatted_data[0]}")
    else:
        logging.warning("Formatting returned empty results!")
    
    # Total time
    metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return formatted_data, metrics


def perform_keyword_search(vec_store, table_name, query, limit):
    """Perform keyword search using vector store.
    
    Executes a keyword-based search using PostgreSQL's full-text search capabilities
    through the VectorStore interface. Also times the keyword extraction step separately.
    
    Args:
        vec_store (VectorStore): The vector store instance
        table_name (str): The database table to search in
        query (str): The search query text
        limit (int): Maximum number of results to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Search results with id, content, search_type, and metadata columns
            - float: Time taken in milliseconds (total)
            - float: Time taken for keyword extraction in milliseconds
    """
    # Time the keyword extraction step
    keyword_extract_start = time.time()
    weighted_keywords = get_keywords(query)
    keyword_extract_ms = round((time.time() - keyword_extract_start) * 1000, 2)

    # Pass the extracted keywords to the vector store (modify signature as needed)
    start_time = time.time()
    keyword_results = vec_store.keyword_search(
        table_name, query, limit=limit, return_dataframe=True, weighted_keywords=weighted_keywords
    )
    keyword_results["search_type"] = "keyword"
    keyword_results = keyword_results[["id", "content", "search_type", "metadata"]]
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return keyword_results, elapsed_ms, keyword_extract_ms


def perform_semantic_search(vec_store, table_name, query, limit):
    """Perform semantic search using vector store.
    
    Executes a semantic vector-based search using pgvector for similarity matching
    through the VectorStore interface.
    
    Args:
        vec_store (VectorStore): The vector store instance
        table_name (str): The database table to search in
        query (str): The search query text
        limit (int): Maximum number of results to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Search results with id, content, search_type, and metadata columns
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Perform semantic search
    semantic_results = vec_store.semantic_search(
        table_name, query, limit=limit, return_dataframe=True
    )
    
    semantic_results["search_type"] = "semantic"
    semantic_results = semantic_results[["id", "content", "search_type", "metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return semantic_results, elapsed_ms


def combine_search_results(keyword_results, semantic_results):
    """Combine keyword and semantic search results.
    
    Concatenates the results from keyword and semantic searches into a single DataFrame.
    
    Args:
        keyword_results (DataFrame): Results from keyword search
        semantic_results (DataFrame): Results from semantic search
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Combined search results
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Combine results
    combined_results = pd.concat([keyword_results, semantic_results], ignore_index=True)
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return combined_results, elapsed_ms


def remove_duplicates(combined_results):
    """Remove duplicate results based on ID.
    
    Removes duplicate entries from the combined results, keeping the first occurrence
    which preserves the original order and prioritization.
    
    Args:
        combined_results (DataFrame): Combined search results potentially with duplicates
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Deduplicated search results
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Remove duplicates, keeping the first occurrence (which maintains the original order)
    deduplicated_results = combined_results.drop_duplicates(subset=["id"], keep="first")
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return deduplicated_results, elapsed_ms


def perform_reranking(query, combined_results, top_n):
    """Re-rank the results using the cross-encoder re-ranker model.
    
    Takes the combined search results and re-ranks them using a more powerful
    cross-encoder model to improve the relevance ordering.
    
    Args:
        query (str): The original search query
        combined_results (DataFrame): Combined search results 
        top_n (int): Number of top results to return after re-ranking
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Re-ranked search results limited to top_n
            - float: Time taken in milliseconds
            - dict: Filtering metrics including exclusion counts
    """
    start_time = time.time()
    
    # Check if input is empty
    if combined_results.empty:
        import logging
        logging.warning("perform_reranking: received empty DataFrame")
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        empty_metrics = {
            "total_chunks_before_filtering": 0,
            "excluded_chunks_count": 0,
            "exclusion_percentage": 0.0,
            "final_chunk_count": 0,
            "score_range_excluded": None,
            "score_range_included": None
        }
        return combined_results, elapsed_ms, empty_metrics
    
    # Re-rank the results using the batch size from config and get metrics
    batch_size = current_app.search_settings.reranker_batch_size
    reranked_results, filtering_metrics = rerank_results_with_metrics(query, combined_results, top_n, batch_size=batch_size)
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return reranked_results, elapsed_ms, filtering_metrics


def hybrid_search(
    table_name: str,
    query: str,
    keyword_k: int = 5,
    semantic_k: int = 5,
    rerank: bool = False,
    top_n: int = 5,
) -> pd.DataFrame:
    """Hybrid search combining keyword and semantic search with optional re-ranking.
    
    Legacy function maintained for backwards compatibility. Use the main search function
    for new implementations.
    
    Args:
        table_name (str): The database table to search in
        query (str): The search query text
        keyword_k (int): Maximum number of keyword search results
        semantic_k (int): Maximum number of semantic search results
        rerank (bool): Whether to re-rank the results
        top_n (int): Number of top results to return after re-ranking
        
    Returns:
        DataFrame: Search results, optionally re-ranked
    """
    vec_store = VectorStore()
    
    # Perform operations using the refactored functions
    keyword_results, _ = perform_keyword_search(vec_store, table_name, query, keyword_k)
    semantic_results, _ = perform_semantic_search(vec_store, table_name, query, semantic_k)
    combined_results, _ = combine_search_results(keyword_results, semantic_results)
    deduplicated_results, _ = remove_duplicates(combined_results)
    
    # Re-rank the results if needed
    if rerank:
        final_results, _, _ = perform_reranking(query, deduplicated_results, top_n)  # Ignore timing and metrics for this legacy function
        return final_results
    
    return deduplicated_results


def format_data(data):
    """Format the search results into a list of dictionaries.
    
    Args:
        data (DataFrame): Search results data
        
    Returns:
        list: List of dictionaries containing formatted document information
    """
    result = []
    
    # Check if data is empty
    if len(data) == 0:
        return result
    
    # Check if results have low confidence (all scores were very low)
    has_low_confidence = False
    if hasattr(data, 'iterrows') and not data.empty:
        # Check if any row has the low_confidence flag
        has_low_confidence = any(row.get('low_confidence', False) for _, row in data.iterrows())
    
    # Process DataFrame directly instead of converting to numpy array
    if hasattr(data, 'iterrows'):
        for idx, row in data.iterrows():
            # Get metadata - it should be in the 'metadata' column
            metadata = row.get('metadata', {})
            document_metadata = row.get('document_metadata', {})

            project_id = metadata.get("project_id")
            document_id = metadata.get("document_id")
            project_name = metadata.get("project_name")
            document_type = get_document_type_name(document_metadata, metadata)  # Pass both document_metadata and chunk metadata
            document_name = metadata.get("document_name")  # Human-readable filename
            document_saved_name = metadata.get("doc_internal_name")  # Technical/hash filename
            page_number = metadata.get("page_number")
            proponent_name = metadata.get("proponent_name")
            s3_key = metadata.get("s3_key")        

            # Append to a list or process as needed
            formatted_result = {
                "document_id": document_id,
                "document_type": document_type,
                "document_name": document_name,
                "document_saved_name": document_saved_name,
                "page_number": page_number,
                "project_id": project_id,
                "project_name": project_name,
                "proponent_name": proponent_name,
                "s3_key": s3_key,
                "content": row.get('content', ''),
                "relevance_score": float(row.get('relevance_score', 0.0)),
                "search_mode": "semantic"  # Indicate this was a semantic search
            }
            
            # Add low confidence warning if applicable
            if has_low_confidence:
                formatted_result["search_quality"] = "low_confidence"
                formatted_result["search_note"] = "Results may not be highly relevant to your query. Consider refining your search terms."
            
            result.append(formatted_result)
    else:
        # Fallback to numpy array processing for backward compatibility
        import numpy as np
        documents = np.array(data)
        
        for i, row in enumerate(documents):
            # Try to intelligently determine the structure based on row length and content
            if len(row) >= 6:
                # Semantic search format with document_metadata: id, metadata, content, embedding, document_metadata, similarity
                metadata = row[1] if len(row) > 1 else {}
                content = row[2] if len(row) > 2 else ''
                document_metadata = row[4] if len(row) > 4 else {}
                relevance_score = float(row[5]) if len(row) > 5 else 0.0
            elif len(row) >= 5:
                # Check if this is a 5-column format with document_metadata or without
                # If row[3] looks like a dict/JSON, it might be document_metadata
                # If row[4] is a float, it's likely the score
                try:
                    score_candidate = float(row[4])
                    # This looks like: id, content, metadata, document_metadata, rank
                    content = row[1] if len(row) > 1 else ''
                    metadata = row[2] if len(row) > 2 else {}
                    document_metadata = row[3] if len(row) > 3 else {}
                    relevance_score = score_candidate
                except (ValueError, TypeError):
                    # This looks like: id, metadata, content, embedding, similarity (no document_metadata)
                    metadata = row[1] if len(row) > 1 else {}
                    content = row[2] if len(row) > 2 else ''
                    document_metadata = {}
                    relevance_score = float(row[4]) if len(row) > 4 else 0.0
            else:
                # Fallback for unknown format
                metadata = row[1] if len(row) > 1 else {}
                content = row[2] if len(row) > 2 else ''
                document_metadata = {}
                relevance_score = 0.0

            project_id = metadata.get("project_id")
            document_id = metadata.get("document_id")
            project_name = metadata.get("project_name")
            document_type = get_document_type_name(document_metadata, metadata)  # Pass both document_metadata and chunk metadata
            document_name = metadata.get("document_name")  # Human-readable filename
            document_saved_name = metadata.get("doc_internal_name")  # Technical/hash filename
            page_number = metadata.get("page_number")
            proponent_name = metadata.get("proponent_name")
            s3_key = metadata.get("s3_key")        

            # Append to a list or process as needed
            result.append(
                {
                    "document_id": document_id,
                    "document_type": document_type,
                    "document_name": document_name,
                    "document_saved_name": document_saved_name,
                    "page_number": page_number,
                    "project_id": project_id,
                    "project_name": project_name,
                    "proponent_name": proponent_name,
                    "s3_key": s3_key,
                    "content": content,
                    "relevance_score": relevance_score,
                    "search_mode": "semantic"  # Indicate this was a semantic search
                }
            )
    
    return result


def perform_document_level_search(vec_store, query, limit, project_ids=None, document_type_ids=None):
    """Perform document-level search using keywords, tags, and headings.
    
    Searches the documents table using pre-computed document-level metadata
    to identify the most relevant documents before searching their chunks.
    
    Args:
        vec_store (VectorStore): The vector store instance
        query (str): The search query text
        limit (int): Maximum number of documents to return
        project_ids (list, optional): List of project IDs to filter results
        document_type_ids (list, optional): List of document type IDs to filter results
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Document search results
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Build predicates for project and document type filtering
    predicates = {}
    if project_ids:
        predicates['project_ids'] = project_ids  # Pass as a special key
    if document_type_ids:
        predicates['document_type_ids'] = document_type_ids  # Pass as a special key
    
    # Perform document-level search
    document_results = vec_store.document_level_search(
        query, limit=limit, predicates=predicates, return_dataframe=True
    )
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return document_results, elapsed_ms


def perform_chunk_search_within_documents(vec_store, document_ids, query, limit):
    """Perform semantic search within specific documents' chunks.
    
    Searches the document_chunks table for the most relevant chunks,
    but only within the chunks belonging to the specified documents.
    
    Args:
        vec_store (VectorStore): The vector store instance
        document_ids (list): List of document IDs to search within
        query (str): The search query text
        limit (int): Maximum number of chunks to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Chunk search results with id, content, metadata columns
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Perform chunk search within specific documents
    chunk_results = vec_store.search_chunks_by_documents(
        document_ids, query, limit=limit, return_dataframe=True
    )
    
    # Rename columns to match expected format for format_data function
    if not chunk_results.empty:
        # The search_chunks_by_documents returns: [id, metadata, content, document_id, project_id, similarity]
        chunk_results["search_type"] = "semantic"
        
        # Add empty document_metadata column for compatibility with format_data function
        # Note: We'll populate document_type in the format_data function using chunk metadata when possible
        chunk_results["document_metadata"] = [{}] * len(chunk_results)
        
        # Reorder to match expected structure: id, content, search_type, similarity, metadata, document_metadata
        chunk_results = chunk_results[["id", "content", "search_type", "similarity", "metadata", "document_metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return chunk_results, elapsed_ms


def perform_semantic_search_all_chunks(vec_store, query, limit, project_ids=None, document_type_ids=None):
    """Perform semantic search across all document chunks.
    
    Performs semantic vector search across all document chunks in the database
    when document-level filtering doesn't find relevant documents.
    This ensures comprehensive coverage even when the document-level
    keywords/tags don't match the query terms.
    
    Args:
        vec_store (VectorStore): The vector store instance
        query (str): The search query text
        limit (int): Maximum number of results to return
        project_ids (list, optional): List of project IDs to filter results
        document_type_ids (list, optional): List of document type IDs to filter results
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Search results with id, content, search_type, and metadata columns
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Use the configured table name for chunks
    table_name = current_app.vector_settings.vector_table_name
    
    # Build predicates for project and document type filtering
    predicates = {}
    if project_ids:
        predicates['project_ids'] = project_ids  # Pass as a special key
    if document_type_ids:
        predicates['document_type_ids'] = document_type_ids  # Pass as a special key
    
    # Debug logging
    import logging
    logging.info(f"Semantic search all chunks - table: {table_name}, query: '{query}', limit: {limit}, predicates: {predicates}")
    
    # Perform semantic search on all chunks
    semantic_results = vec_store.semantic_search(
        table_name, query, limit=limit, predicates=predicates, return_dataframe=True
    )
    
    if not semantic_results.empty:
        semantic_results["search_type"] = "semantic"
        
        # Add empty document_metadata column for compatibility with format_data function  
        semantic_results["document_metadata"] = [{}] * len(semantic_results)
        
        # For semantic search on all chunks, semantic_search returns: [id, metadata, content, embedding, similarity]
        # We need to reorder to: [id, content, search_type, similarity, metadata, document_metadata]
        semantic_results = semantic_results[["id", "content", "search_type", "similarity", "metadata", "document_metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return semantic_results, elapsed_ms


def document_similarity_search(document_id, project_ids=None, limit=10):
    """Find documents similar to the specified document using document-level embeddings.
    
    This function performs cosine similarity search on document-level embeddings
    to find documents that are semantically similar to the source document.
    
    Args:
        document_id (str): The ID of the document to find similar documents for
        project_ids (list, optional): List of project IDs to filter results
        limit (int): Maximum number of similar documents to return
        
    Returns:
        tuple: A tuple containing:
            - list: Formatted similar documents as a list of dictionaries
            - dict: Search performance metrics in milliseconds
    """
    metrics = {}
    start_time = time.time()
    
    # Instantiate VectorStore
    vec_store = VectorStore()
    
    # Step 1: Get the embedding for the source document
    source_embedding, embedding_time = get_document_embedding(vec_store, document_id)
    metrics["embedding_retrieval_ms"] = embedding_time
    
    if source_embedding is None:
        # Document not found
        metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
        return [], metrics
    
    # Step 2: Perform similarity search against other documents
    similar_docs, similarity_time = perform_document_similarity_search(
        vec_store, source_embedding, document_id, project_ids, limit
    )
    metrics["similarity_search_ms"] = similarity_time
    
    # Step 3: Format the results
    format_start = time.time()
    formatted_docs = format_similar_documents(similar_docs)
    metrics["formatting_ms"] = round((time.time() - format_start) * 1000, 2)
    
    # Total time
    metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return formatted_docs, metrics


def get_document_embedding(vec_store, document_id):
    """Retrieve the embedding vector for a specific document.
    
    Args:
        vec_store (VectorStore): The vector store instance
        document_id (str): The document ID to get embedding for
        
    Returns:
        tuple: A tuple containing:
            - numpy.array or None: The document embedding vector, or None if not found
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    embedding = vec_store.get_document_embedding(document_id)
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return embedding, elapsed_ms


def perform_document_similarity_search(vec_store, source_embedding, exclude_document_id, project_ids, limit):
    """Perform cosine similarity search against document embeddings.
    
    Args:
        vec_store (VectorStore): The vector store instance
        source_embedding (numpy.array): The embedding vector to search for similar documents
        exclude_document_id (str): Document ID to exclude from results (the source document)
        project_ids (list, optional): List of project IDs to filter results
        limit (int): Maximum number of similar documents to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Similar documents with similarity scores
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Build predicates for project filtering
    predicates = {}
    if project_ids:
        predicates['project_ids'] = project_ids
    
    # Perform similarity search
    similar_documents = vec_store.document_similarity_search(
        source_embedding, exclude_document_id, predicates, limit, return_dataframe=True
    )
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return similar_documents, elapsed_ms


def format_similar_documents(similar_docs_df):
    """Format similar documents results for API response.
    
    Args:
        similar_docs_df (DataFrame): DataFrame containing similar documents
        
    Returns:
        list: List of formatted document dictionaries
    """
    if similar_docs_df.empty:
        return []
    
    formatted_docs = []
    for _, row in similar_docs_df.iterrows():
        # Get document metadata
        document_metadata = row.get('document_metadata', {})
        if isinstance(document_metadata, str):
            import json
            try:
                document_metadata = json.loads(document_metadata)
            except:
                document_metadata = {}
        elif document_metadata is None:
            document_metadata = {}
        
        # Extract fields from document metadata with correct mapping based on user example
        document_type = document_metadata.get("document_type") or get_document_type_name(document_metadata, None)
        
        # Based on user example: document_name should be human-readable filename
        document_name = document_metadata.get("document_name")  # Human-readable filename
        
        # Based on user example: document_saved_name should be hash/technical filename
        # Try the direct field first, then fallbacks
        document_saved_name = (document_metadata.get("document_saved_name") or 
                              document_metadata.get("doc_internal_name") or 
                              document_metadata.get("document_internal_name") or
                              document_metadata.get("internal_name") or
                              document_metadata.get("file_name") or
                              document_metadata.get("filename"))
                              
        project_name = document_metadata.get("project_name")
        proponent_name = document_metadata.get("proponent_name")
        s3_key = document_metadata.get("s3_key")
        
        doc = {
            "document_id": row["document_id"],
            "document_type": document_type,
            "document_name": document_name,
            "document_saved_name": document_saved_name,
            "project_id": row.get("project_id"),
            "project_name": project_name,
            "proponent_name": proponent_name,
            "s3_key": s3_key,
            "similarity_score": round(float(row["similarity"]), 4)
        }
        formatted_docs.append(doc)
    
    return formatted_docs


def is_generic_document_request(query: str) -> bool:
    """Check if the query is a generic document request (not seeking specific content).
    
    Generic queries are those that ask for documents of a certain type without
    seeking specific information within those documents. Queries with content-specific
    terms (like 'complaints', 'concerns', 'issues') should use semantic search.
    
    Args:
        query (str): The search query text
        
    Returns:
        bool: True if the query is generic, False otherwise
    """
    # First check for content-specific terms that indicate semantic search is needed
    content_specific_terms = [
        r'\b(complaints?|concerns?|issues?|problems?|violations?|incidents?)\b',
        r'\b(about|regarding|related to|concerning)\b',
        r'\b(contain|containing|with|have|having|include|including)\b',
        r'\b(mention|mentioning|discuss|discussing|address|addressing)\b',
        r'\b(refer|referring|reference|references)\s+(to|the|a|an)\b',
        r'\b(talk|talking|speak|speaking)\s+(about|of|on)\b',
        r'\b(environmental|safety|health|regulatory|compliance)\b',
        r'\b(impact|effect|consequence|result|outcome)\b',
        r'\bthat\s+(talk|speak|discuss|mention|refer|address|cover)\b',
        r'\b(nation|first nation|indigenous|aboriginal|métis|inuit)\b'
    ]
    
    query_lower = query.lower()
    
    # If query contains content-specific terms, it's NOT generic
    for pattern in content_specific_terms:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return False
    
    # Check for truly generic patterns (asking for documents without specific content)
    generic_patterns = [
        # Patterns with explicit project references (for project inference)
        r'\b(any|all)\s+(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\bshow\s+me\s+(all|any)?\s*(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\bfind\s+(all|any)?\s*(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\bget\s+(all|any)?\s*(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\blist\s+(all|any)?\s*(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\blooking\s+for\s+(any|all)\s+(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\bneed\s+(any|all)\s+(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        r'\bprovide\s+(any|all)\s+(correspondence|letters?|documents?|files?)\s+(for|from)\b',
        
        # Patterns for when project/type filtering is provided via API (no "for/from" needed)
        r'\b(any|all)\s+(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\bshow\s+me\s+(all|any)?\s*(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\bfind\s+(all|any)?\s*(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\bget\s+(all|any)?\s*(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\blist\s+(all|any)?\s*(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\blooking\s+for\s+(any|all)\s+(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\bneed\s+(any|all)\s+(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        r'\bprovide\s+(any|all)\s+(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\b',
        
        # Simpler patterns for direct document type requests
        r'^\s*(?:show me |give me |find |get |list )?(?:any |all )?(?:the\s+)?(correspondence|letters?|documents?|files?|reports?|studies|assessments?|analyses|plans?|orders?|agreements?|contracts?|certificates?|permits?|licenses?)\s*\??\s*$',
        
        # More specific patterns for pure document requests
        r'^\s*(?:show me |give me |find |get |list )?(?:any |all )?(?:the )?(?:correspondence|letters?|documents?|files?)\s+(?:for|from|related to)\s+[^?]*\??\s*$'
    ]
    
    for pattern in generic_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            return True
    
    return False


def perform_direct_metadata_search(vec_store, project_ids, document_type_ids, limit):
    """Perform direct metadata-based document search without semantic analysis.
    
    This function is used when both project and document type are confidently inferred
    and the query is generic (e.g., "any correspondence for Project X"). Instead of
    semantic search, it returns all documents matching the metadata criteria,
    ordered by document date.
    
    Args:
        vec_store (VectorStore): The vector store instance
        project_ids (list): List of project IDs to filter results
        document_type_ids (list): List of document type IDs to filter results
        limit (int): Maximum number of documents to return
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Document results ordered by date
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Get documents directly by metadata filtering
    documents = vec_store.get_documents_by_metadata(
        project_ids=project_ids,
        document_type_ids=document_type_ids,
        order_by="document_date DESC",  # Order by date, newest first
        limit=limit,
        return_dataframe=True
    )
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return documents, elapsed_ms


def format_document_data(documents_df):
    """Format document-level search results into a list of dictionaries.
    
    Args:
        documents_df (DataFrame): Document-level search results data
        
    Returns:
        list: List of dictionaries containing formatted document information
    """
    result = []
    
    # Check if data is empty
    if len(documents_df) == 0:
        return result
    
    # Process DataFrame directly
    if hasattr(documents_df, 'iterrows'):
        for idx, row in documents_df.iterrows():
            # Extract document information directly from the DataFrame columns
            # The get_documents_by_metadata function already extracts JSON fields into columns
            document_id = str(row.get("document_id", ""))
            project_id = str(row.get("project_id", ""))
            
            # These fields are extracted from document_metadata JSON in the SQL query
            document_name = row.get("document_name")
            document_saved_name = row.get("document_saved_name") 
            project_name = row.get("project_name")
            proponent_name = row.get("proponent_name")
            s3_key = row.get("s3_key")
            document_date = row.get("document_date")
            
            # Get document type - try from metadata JSON first, then fallback to helper function
            document_metadata = row.get('document_metadata', {})
            if isinstance(document_metadata, str):
                import json
                try:
                    document_metadata = json.loads(document_metadata)
                except:
                    document_metadata = {}
            elif document_metadata is None:
                document_metadata = {}
            
            document_type = document_metadata.get("document_type") or get_document_type_name(document_metadata, None)
            
            # For document-level results, content is typically a summary or first chunk
            content = row.get('content', '') or row.get('document_summary', '') or "Full document available"

            # Append to result list
            formatted_result = {
                "document_id": document_id,
                "document_type": document_type,
                "document_name": document_name,
                "document_saved_name": document_saved_name,
                "document_date": document_date,
                "page_number": None,  # Not applicable for document-level results
                "project_id": project_id,
                "project_name": project_name,
                "proponent_name": proponent_name,
                "s3_key": s3_key,
                "content": content,
                "relevance_score": 1.0,  # Perfect relevance for metadata matches
                "search_mode": "document_metadata"  # Indicate this was a metadata search
            }
            
            result.append(formatted_result)
    
    return result
