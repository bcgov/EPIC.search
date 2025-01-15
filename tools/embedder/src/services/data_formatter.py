
def format_metadata(project_info, file_info):
    
    return {
                "project_id": project_info.get("_id"),
                "project_name": project_info.get("name"),
                "proponent_name" : project_info.get("proponent", {}).get("name"),
                "document_name":  file_info.get("documentFileName"),
                "doc_internal_name": file_info.get("internalURL", "").split('/')[-1],
                "created_at": file_info.get("documentDate"),
                "document_id" :file_info.get("_id"),
                # Add other relevant fields if needed
    }

def aggregate_tags_by_chunk(results):
    aggregated = {}
    
    for item in results["tags_and_chunks"]:
        chunk_id = item["chunk_id"]  
        if chunk_id not in aggregated:
            aggregated[chunk_id] = {
                "chunk_id": chunk_id,
                "chunk_metadata": item["chunk_metadata"],
                "chunk_text": item["chunk_text"],
                "chunk_embedding": item["chunk_embedding"],
                "tags": []
            }
        
        aggregated[chunk_id]["tags"].append(item["tag"])

    for chunk_id in aggregated:
        aggregated[chunk_id]["tags"] = list(set(aggregated[chunk_id]["tags"]))
    
    return aggregated