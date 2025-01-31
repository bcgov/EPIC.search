import pandas as pd
from .re_raker import rerank_results
from .vector_store import VectorStore
from flask import current_app
import numpy as np

def search(question
    ) -> pd.DataFrame:
      table_name= current_app.config['VECTOR_TABLE']
      keyword_k= current_app.config['KEYWORD_FETCH_COUNT']
      semantic_k= current_app.config['SEMANTIC_FETCH_COUNT']
      top_n: int = current_app.config['TOP_RECORD_COUNT']
      data = hybrid_search(table_name,question,keyword_k,semantic_k,True,top_n)
      return format_data(data)
      


def hybrid_search(
        table_name : str,
        query: str,
        keyword_k: int = 5,
        semantic_k: int = 5,
        rerank: bool = False,
        top_n: int = 5,
    ) -> pd.DataFrame:
        
        vec_store = VectorStore()
        keyword_results = vec_store.keyword_search(
           table_name, query, limit=keyword_k, return_dataframe=True
        )
        keyword_results["search_type"] = "keyword"
        keyword_results = keyword_results[["id", "content", "search_type", "metadata"]]

        # Perform semantic search
        semantic_results = vec_store.semantic_search(
            table_name, query, limit=semantic_k, return_dataframe=True
        )
        semantic_results["search_type"] = "semantic"
        semantic_results = semantic_results[["id", "content", "search_type", "metadata"]]

        # Combine results
        combined_results = pd.concat(
            [keyword_results, semantic_results], ignore_index=True
        )

        # Remove duplicates, keeping the first occurrence (which maintains the original order)
        combined_results = combined_results.drop_duplicates(subset=["id"], keep="first")

        if rerank:
            return rerank_results(query, combined_results, top_n)

        return combined_results

def format_data(data):
        result=[]
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
            
            # Append to a list or process as needed
            result.append({
                "document_id": document_id,
                "document_type" :document_type,
                "document_name": document_name,
                "document_saved_name" : document_saved_name,
                "page_number": page_number,
                "project_id" : project_id,
                "project_name" : project_name,
                "content" :  row[1]
            })
        return result