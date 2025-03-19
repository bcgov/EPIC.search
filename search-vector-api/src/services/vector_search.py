import pandas as pd
import time
from .re_ranker import rerank_results
from .vector_store import VectorStore
from flask import current_app
import numpy as np


def search(question):
    """Main search function that combines all search operations."""
    metrics = {}
    start_time = time.time()
    
    table_name = current_app.config["VECTOR_TABLE"]
    keyword_k = current_app.config["KEYWORD_FETCH_COUNT"]
    semantic_k = current_app.config["SEMANTIC_FETCH_COUNT"]
    top_n = current_app.config["TOP_RECORD_COUNT"]
    
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
    
    # Re-rank results if needed
    if True:  # Always rerank for now
        reranked_results, rerank_time = perform_reranking(question, deduplicated_results, top_n)
        metrics["reranking_ms"] = rerank_time
        results = reranked_results
    else:
        results = deduplicated_results    
    
    # Format the data
    format_start = time.time()
    formatted_data = format_data(results)
    metrics["formatting_ms"] = round((time.time() - format_start) * 1000, 2)
    
    # Total time
    metrics["total_search_ms"] = round((time.time() - start_time) * 1000, 2)
    
    return formatted_data, metrics


def perform_keyword_search(vec_store, table_name, query, limit):
    """Perform keyword search using vector store."""
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
    """Perform semantic search using vector store."""
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
    """Combine keyword and semantic search results."""
    start_time = time.time()
    
    # Combine results
    combined_results = pd.concat([keyword_results, semantic_results], ignore_index=True)
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return combined_results, elapsed_ms


def remove_duplicates(combined_results):
    """Remove duplicate results based on ID."""
    start_time = time.time()
    
    # Remove duplicates, keeping the first occurrence (which maintains the original order)
    deduplicated_results = combined_results.drop_duplicates(subset=["id"], keep="first")
    
    elapsed_ms = round((time.time() - start_time) * 1000, 2)
    return deduplicated_results, elapsed_ms


def perform_reranking(query, combined_results, top_n):
    """Re-rank the results using the re-ranker."""
    start_time = time.time()
    
    # Re-rank the results
    reranked_results = rerank_results(query, combined_results, top_n)
    
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
    """Legacy function for backwards compatibility."""
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
    """Format the search results into a list of dictionaries."""
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
                "content": row[1],
            }
        )
    return result
