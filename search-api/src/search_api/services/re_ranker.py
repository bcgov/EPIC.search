import pandas as pd    
from sentence_transformers import CrossEncoder

def rerank_results(
     query: str, items: pd.DataFrame, top_n: int
    ) -> pd.DataFrame:
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        documents=items["content"].tolist()
        pairs = [[query, doc] for doc in documents]
        scores = model.predict(pairs)
        reranked_df = pd.DataFrame(
            [
                {
                    "id": result["id"],
                    "content": result["content"],
                    "search_type": result["search_type"],
                    "relevance_score": scores[i],
                    "metadata": result["metadata"],
                }
               for i, (_, result) in enumerate(items.iterrows())
            ]
        )
        sorted_df = reranked_df.sort_values("relevance_score", ascending=False)
        top_n_records = sorted_df.head(int(top_n))
      
        return top_n_records