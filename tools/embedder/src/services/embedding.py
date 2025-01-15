from nomic import embed
import numpy as np


def get_embedding(texts):
    output = embed.text(
        texts=texts,
        model='nomic-embed-text-v1',
        inference_mode='local',
        task_type='search_document',
        dimensionality=768,
    )
    return output['embeddings']

