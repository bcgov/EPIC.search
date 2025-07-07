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
from .re_ranker import rerank_results
from .vector_store import VectorStore


def search(question, project_ids=None):
    """Main search function implementing a two-stage search strategy.
    
    This function orchestrates a modern search pipeline that leverages document-level
    metadata for improved efficiency and accuracy:
    
    Stage 1: Document-level filtering using pre-computed keywords, tags, and headings
    Stage 2: Semantic search within relevant document chunks
    
    This approach is much more efficient than searching all chunks and provides
    better relevance by first identifying the most promising documents.
    
    Args:
        question (str): The search query text
        project_ids (list, optional): List of project IDs to filter results.
                                    If None or empty, searches across all projects.
        
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
    
    # Stage 1: Find relevant documents using document-level metadata
    relevant_documents, doc_search_time = perform_document_level_search(vec_store, question, doc_limit, project_ids)
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
        # Fallback: if no documents found, perform traditional search with project filtering
        logging.info("Stage 2 - No documents found, using fallback search")
        chunk_results, fallback_time = perform_fallback_search(vec_store, question, chunk_limit, project_ids)
        metrics["fallback_search_ms"] = fallback_time
        logging.info(f"Fallback search found {len(chunk_results) if not chunk_results.empty else 0} chunks")
    
    # If both document search and fallback search returned no results, try a simple keyword search
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
    reranked_results, rerank_time = perform_reranking(question, chunk_results, top_n)
    metrics["reranking_ms"] = rerank_time
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
    """
    start_time = time.time()
    
    # Check if input is empty
    if combined_results.empty:
        import logging
        logging.warning("perform_reranking: received empty DataFrame")
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return combined_results, elapsed_ms
    
    # Re-rank the results using the batch size from config
    batch_size = current_app.search_settings.reranker_batch_size
    reranked_results = rerank_results(query, combined_results, top_n, batch_size=batch_size)
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return reranked_results, elapsed_ms


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
        final_results, _ = perform_reranking(query, deduplicated_results, top_n)
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

            project_id = metadata.get("project_id")
            document_id = metadata.get("document_id")
            project_name = metadata.get("project_name")
            document_type = metadata.get("document_type")
            document_name = metadata.get("doc_internal_name")
            document_saved_name = metadata.get("document_name")
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
            # row[4] contains the metadata dictionary
            metadata = row[4] if len(row) > 4 else {}

            project_id = metadata.get("project_id")
            document_id = metadata.get("document_id")
            project_name = metadata.get("project_name")
            document_type = metadata.get("document_type")
            document_name = metadata.get("doc_internal_name")
            document_saved_name = metadata.get("document_name")
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
                    "content": row[1] if len(row) > 1 else '',
                    "relevance_score": float(row[3]) if len(row) > 3 else 0.0,
                }
            )
    
    return result


def perform_document_level_search(vec_store, query, limit, project_ids=None):
    """Perform document-level search using keywords, tags, and headings.
    
    Searches the documents table using pre-computed document-level metadata
    to identify the most relevant documents before searching their chunks.
    
    Args:
        vec_store (VectorStore): The vector store instance
        query (str): The search query text
        limit (int): Maximum number of documents to return
        project_ids (list, optional): List of project IDs to filter results
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Document search results
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Build predicates for project filtering
    predicates = {}
    if project_ids:
        predicates['project_ids'] = project_ids  # Pass as a special key
    
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
        # The search_chunks_by_documents already returns the correct column names
        # [id, metadata, content, document_id, project_id, similarity]
        chunk_results["search_type"] = "semantic"
        # Reorder to match expected structure: id, content, search_type, similarity, metadata
        chunk_results = chunk_results[["id", "content", "search_type", "similarity", "metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return chunk_results, elapsed_ms


def perform_fallback_search(vec_store, query, limit, project_ids=None):
    """Perform fallback search when no relevant documents are found.
    
    Falls back to the traditional approach of searching all chunks
    when document-level search doesn't find relevant documents.
    
    Args:
        vec_store (VectorStore): The vector store instance
        query (str): The search query text
        limit (int): Maximum number of results to return
        project_ids (list, optional): List of project IDs to filter results
        
    Returns:
        tuple: A tuple containing:
            - DataFrame: Search results with id, content, search_type, and metadata columns
            - float: Time taken in milliseconds
    """
    start_time = time.time()
    
    # Use the configured table name for chunks
    table_name = current_app.vector_settings.vector_table_name
    
    # Build predicates for project filtering
    predicates = {}
    if project_ids:
        predicates['project_ids'] = project_ids  # Pass as a special key
    
    # Debug logging
    import logging
    logging.info(f"Fallback search - table: {table_name}, query: '{query}', limit: {limit}, predicates: {predicates}")
    
    # Perform semantic search on all chunks as fallback
    semantic_results = vec_store.semantic_search(
        table_name, query, limit=limit, predicates=predicates, return_dataframe=True
    )
    
    if not semantic_results.empty:
        semantic_results["search_type"] = "semantic"
        # The semantic_search returns: [id, metadata, content, embedding, similarity]
        # We need to reorder to: [id, content, search_type, similarity, metadata]
        semantic_results = semantic_results[["id", "content", "search_type", "similarity", "metadata"]]
    
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
        doc = {
            "document_id": row["document_id"],
            "document_keywords": row.get("document_keywords"),
            "document_tags": row.get("document_tags"), 
            "document_headings": row.get("document_headings"),
            "project_id": row.get("project_id"),
            "similarity_score": round(float(row["similarity"]), 4),
            "created_at": row.get("created_at").isoformat() if row.get("created_at") else None
        }
        formatted_docs.append(doc)
    
    return formatted_docs
