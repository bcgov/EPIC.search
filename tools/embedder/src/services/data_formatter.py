"""
Data Formatter module for transforming and organizing document metadata and tags.

This module provides utility functions to format document metadata from API responses
and to aggregate document tags that belong to the same text chunk.
"""

def format_metadata(project_info, file_info):
    """
    Format project and file information into a standardized metadata dictionary.
    
    Extracts relevant fields from the project and file information objects and
    combines them into a unified metadata dictionary for storage with document chunks.
    
    Args:
        project_info (dict): Project information from the API
        file_info (dict): File information from the API
        
    Returns:
        dict: A formatted metadata dictionary with standardized field names
    """
    return {
        "project_id": project_info.get("_id"),
        "project_name": project_info.get("name"),
        "proponent_name": project_info.get("proponent", {}).get("name"),
        "document_name": file_info.get("documentFileName"),
        "doc_internal_name": file_info.get("internalURL", "").split("/")[-1],
        "created_at": file_info.get("documentDate"),
        "document_id": file_info.get("_id"),
        # Add other relevant fields if needed
    }


def aggregate_tags_by_chunk(results):
    """
    Aggregate tags by chunk ID to avoid duplicate storage of chunks.
    
    Given a list of chunk-tag pairs, this function creates a dictionary where each
    unique chunk has a single entry with all its associated tags combined into a list.
    Duplicate tags are removed.
    
    Args:
        results (dict): Dictionary containing a 'tags_and_chunks' list, where each item
                        has chunk information and a single tag
        
    Returns:
        dict: Dictionary with chunk IDs as keys and objects containing chunk data and
              a deduplicated list of tags as values
    """
    aggregated = {}

    for item in results["tags_and_chunks"]:
        chunk_id = item["chunk_id"]
        if chunk_id not in aggregated:
            aggregated[chunk_id] = {
                "chunk_id": chunk_id,
                "chunk_metadata": item["chunk_metadata"],
                "chunk_text": item["chunk_text"],
                "chunk_embedding": item["chunk_embedding"],
                "tags": [],
            }

        aggregated[chunk_id]["tags"].append(item["tag"])

    for chunk_id in aggregated:
        aggregated[chunk_id]["tags"] = list(set(aggregated[chunk_id]["tags"]))

    return aggregated
