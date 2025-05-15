import os
import pandas as pd
from sentence_transformers import CrossEncoder
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cross_encoder():
    """Return a cached instance of the CrossEncoder model."""
    model = os.getenv("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-2-v2")
    return CrossEncoder(model)     

def rerank_results(query: str, items: pd.DataFrame, top_n: int) -> pd.DataFrame:
    # Use the cached model instead of creating a new one each time
    model = get_cross_encoder()
    
    documents = items["content"].tolist()
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
