from .vector_store import VectorStore
def init_vec_db():
    vec = VectorStore()
    vec.create_table("document_details")
    vec.create_table("document_tags")