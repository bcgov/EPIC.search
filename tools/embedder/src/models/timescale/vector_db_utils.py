from .vector_store import VectorStore
import os
def init_vec_db():
    vec = VectorStore()
    vec.create_table(os.environ.get("INDEX_TABLE_NAME"))
    vec.create_table(os.environ.get("CHUNK_DUMP_TABLE_NAME"))