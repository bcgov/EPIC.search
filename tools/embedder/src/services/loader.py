import os
import uuid
import tempfile
import pymupdf4llm
import strip_markdown

from .s3_reader import read_file_from_s3
from src.models import VectorStore
from .markdown_splitter import chunk_markdown_text
from .tag_extractor import explicit_and_semantic_search_large_document
from .data_formatter import aggregate_tags_by_chunk
from .embedding import get_embedding
def load_data(s3_key, base_metadata):
    temp_path = None
    try:
        pdf_bytes = read_file_from_s3(s3_key)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp.write(pdf_bytes)
            temp.flush()
            temp_path = temp.name

        pages = pymupdf4llm.to_markdown(temp_path, page_chunks=True)

        vec = VectorStore()

        headers = ["Header 1", "Header 2", "Header 3", "Header 4", "Header 5", "Header 6"]
        all_pages_text = []
        data_to_upsert = []

        for page_index, page_markdown in enumerate(pages):
            if not page_markdown["text"].strip():
                continue

            chunks = chunk_markdown_text(page_markdown["text"])
            if not chunks:
                print(f"No chunks found on page {page_index+1} of {s3_key}")
                continue

            chunk_texts = []
            chunk_metadatas = []

            for chunk in chunks:
                if not hasattr(chunk, "page_content"):
                    continue

                chunk_text = strip_markdown.strip_markdown(chunk.page_content).strip()
                if not chunk_text:
                    continue

                all_pages_text.append(chunk_text)
                chunk_data = chunk.metadata if chunk.metadata else {}
                headings = [chunk_data.get(h, "") for h in headers]

                chunk_metadata = {
                    **base_metadata,
                    "page_number": str(page_index + 1),
                    "headings": headings
                }
                chunk_texts.append(chunk_text)
                chunk_metadatas.append(chunk_metadata)

            if chunk_texts:
                embeddings = get_embedding(chunk_texts)
                for i, text in enumerate(chunk_texts):
                    record_id = str(uuid.uuid1())
                    record = (
                        record_id,  
                        chunk_metadatas[i],  
                        text, 
                        embeddings[i],
                    )
                    data_to_upsert.append(record)

        if not data_to_upsert:
            raise ValueError(f"No valid text content found in file {s3_key}")

        vec.upsert(os.environ.get("CHUNK_DUMB_TABLE_NAME"), data_to_upsert)

    
        # Extract tags
        tags = explicit_and_semantic_search_large_document(data_to_upsert)
        unique_tags = aggregate_tags_by_chunk(tags)
        tags_to_upsert = []
        for chunk_id, chunk_info in unique_tags.items():
            if chunk_info:
                tag_metadata = chunk_info["chunk_metadata"]
                tag_metadata["tags"] = chunk_info["tags"]
                tag_record = (
                    str(uuid.uuid1()),
                    tag_metadata,
                    chunk_info["chunk_text"],
                    chunk_info["chunk_embedding"],
                )
                tags_to_upsert.append(tag_record)
        vec.upsert(os.environ.get("INDEX_TABLE_NAME"), tags_to_upsert)

        return s3_key

    except Exception as e:
        print(f"Exception processing {s3_key}: {e}")
        raise
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
