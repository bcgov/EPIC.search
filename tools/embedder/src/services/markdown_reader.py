import pymupdf4llm

def read_as_pages(path):
     pages = pymupdf4llm.to_markdown(path, page_chunks=True)
     return pages