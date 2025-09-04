import pymupdf4llm
import fitz  # PyMuPDF

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
    
    Includes fallback handling for PyMuPDF4LLM errors like "list index out of range".
    
    Args:
        path (str): Path to the PDF file to convert
        
    Returns:
        list: A list of dictionaries, each containing the markdown text for a single page
              and any metadata extracted from the document
    """
    try:
        # Try PyMuPDF4LLM markdown extraction (preferred method)
        pages = pymupdf4llm.to_markdown(path, page_chunks=True)
        if pages and len(pages) > 0:
            # Check if pymupdf4llm returned valid content or just formatting characters
            total_meaningful_chars = 0
            for page in pages:
                text = page.get("text", "").strip()
                # Count characters that aren't just formatting (dashes, newlines, etc.)
                meaningful_chars = len([c for c in text if c not in ['-', '\n', '\r', ' ', '\t']])
                total_meaningful_chars += meaningful_chars
            
            # If we have very little meaningful content, consider it a failure
            if total_meaningful_chars < 10:  # Threshold for meaningful content
                print(f"[WARN] PyMuPDF4LLM returned only formatting characters ({total_meaningful_chars} meaningful chars) for {path}, falling back to basic text extraction")
                raise ValueError("Insufficient meaningful content from PyMuPDF4LLM")
            
            return pages
        else:
            print(f"[WARN] PyMuPDF4LLM returned empty pages for {path}, falling back to basic text extraction")
            raise ValueError("Empty pages returned from PyMuPDF4LLM")
            
    except (IndexError, ValueError, Exception) as e:
        print(f"[WARN] PyMuPDF4LLM failed for {path}: {type(e).__name__}: {e}")
        print(f"[FALLBACK] Using basic PyMuPDF text extraction instead")
        
        # Fallback to basic PyMuPDF text extraction
        try:
            doc = fitz.open(path)
            pages = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                text = page.get_text()
                
                # Format similar to pymupdf4llm output
                page_data = {
                    "text": text,
                    "page": page_num + 1,
                    "metadata": {
                        "source": "pymupdf_fallback",
                        "page_number": page_num + 1
                    }
                }
                pages.append(page_data)
            
            doc.close()
            
            if pages:
                print(f"[FALLBACK] Successfully extracted {len(pages)} pages using basic PyMuPDF")
                return pages
            else:
                print(f"[ERROR] Both PyMuPDF4LLM and PyMuPDF fallback failed for {path}")
                return []
                
        except Exception as fallback_error:
            print(f"[ERROR] Fallback extraction also failed for {path}: {fallback_error}")
            return []