import pymupdf4llm

"""
Markdown Reader module for PDF document extraction.

This module provides functionality to convert PDF documents to markdown format,
which is easier to process for text extraction and embedding generation.
It relies on the pymupdf4llm library for PDF processing.
"""

def read_as_pages(path):
    """
    Convert a PDF document to markdown, with content divided by pages.
    
    This function takes a path to a PDF file and converts its content to markdown format,
    preserving the page structure. Each page is returned as a separate markdown text.
    
    Args:
        path (str): Path to the PDF file to convert
        
    Returns:
        list: A list of dictionaries, each containing the markdown text for a single page
              and any metadata extracted from the document
    """
    pages = pymupdf4llm.to_markdown(path, page_chunks=True)
    return pages