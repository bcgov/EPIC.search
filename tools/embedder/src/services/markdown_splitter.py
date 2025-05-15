from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
Markdown Splitter module for chunking markdown documents.

This module provides functionality to split markdown text into smaller, semantically coherent chunks
for embedding and processing. It preserves the header structure of markdown documents
and creates overlapping chunks to maintain context between segments.
"""

def chunk_markdown_text(document_content):
    """
    Split markdown text into smaller, semantically meaningful chunks.
    
    This function processes markdown text in two stages:
    1. First, it splits the text at markdown headers to preserve the document structure
    2. Then, it applies a recursive character-based splitting to create chunks of 
       appropriate size for embedding
    
    The chunk size and overlap are configured in the application settings.
    
    Args:
        document_content (str): The markdown text content to be chunked
        
    Returns:
        list: A list of document chunks with their metadata (including header hierarchy)
        
    Note:
        Each chunk preserves its relationship to the document structure through
        metadata that includes the headers under which it appears.
    """
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]
    splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on, strip_headers=False
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size= int(settings.chunk_settings.chunk_size),
        chunk_overlap= int(settings.chunk_settings.chunk_overlap),
        length_function=len,
        is_separator_regex=False,
    )
    text_markdown = splitter.split_text(document_content)
    splited_text = text_splitter.split_documents(text_markdown)
    return splited_text
