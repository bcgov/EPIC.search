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
import numpy as np

from .re_ranker import rerank_results
from .vector_store import VectorStore


def search(question):
    """Main search function that combines all search operations.
    
    This function orchestrates the complete search pipeline, performing both
    semantic and keyword searches, combining results, removing duplicates,
    re-ranking, and formatting the final response.
    
    Args:
        question (str): The search query text
        
    Returns:
        tuple: A tuple containing:
            - list: Formatted search results as a list of dictionaries
            - dict: Search performance metrics in milliseconds for each search stage
    """
    metrics = {}
    start_time = time.time()
    
    # Use strongly typed configuration properties
    table_name = current_app.vector_settings.vector_table_name
    keyword_k = current_app.search_settings.keyword_fetch_count
    semantic_k = current_app.search_settings.semantic_fetch_count
    top_n = current_app.search_settings.top_record_count
    
    # Instantiate VectorStore
    vec_store = VectorStore()
    
    # Perform keyword search
    keyword_results, keyword_time = perform_keyword_search(vec_store, table_name, question, keyword_k)
    metrics["keyword_search_ms"] = keyword_time
    
    # Perform semantic search
    semantic_results, semantic_time = perform_semantic_search(vec_store, table_name, question, semantic_k)
    metrics["semantic_search_ms"] = semantic_time
    
    # Combine results
    combined_results, combine_time = combine_search_results(keyword_results, semantic_results)
    metrics["combine_results_ms"] = combine_time
    
    # Remove duplicates
    deduplicated_results, dedup_time = remove_duplicates(combined_results)
    metrics["deduplication_ms"] = dedup_time
    
    # Re-rank results    
    reranked_results, rerank_time = perform_reranking(question, deduplicated_results, top_n)
    metrics["reranking_ms"] = rerank_time
    results = reranked_results    
    
    # Format the data
    format_start = time.time()
    formatted_data = format_data(results)
    metrics["formatting_ms"] = round((time.time() - format_start) * 1000, 2)
    
    # Total time
    metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return formatted_data, metrics


def perform_keyword_search(vec_store, table_name, query, limit):
    """Perform keyword search using vector store.
    
    Executes a keyword-based search using PostgreSQL's full-text search capabilities
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
    
    # Perform keyword search
    keyword_results = vec_store.keyword_search(
        table_name, query, limit=limit, return_dataframe=True
    )
    
    keyword_results["search_type"] = "keyword"
    keyword_results = keyword_results[["id", "content", "search_type", "metadata"]]
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return keyword_results, elapsed_ms


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
    documents = np.array(data)
    for row in documents:
        # row[4] contains the metadata dictionary
        metadata = row[4]

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
                "content": row[1],
                "relevance_score": float(row[3]) if len(row) > 3 else None,
            }
        )
    return result
