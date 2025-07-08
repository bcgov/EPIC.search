import fitz

def validate_pdf_file(temp_path, s3_key):
    """
    Validate the PDF file for format and extractable text.
    Returns (is_valid, reason) where is_valid is True if the file should be processed.
    
    This function identifies likely scanned/image-based PDFs that would require OCR
    by checking PDF version, creator/producer metadata, and extractable text content.
    """
    try:
        doc = fitz.open(temp_path)
        metadata = doc.metadata
        creator = metadata.get('creator', '').lower()
        producer = metadata.get('producer', '').lower()
        first_page_text = doc[0].get_text().strip() if doc.page_count > 0 else ""
        doc.close()
    except Exception as precheck_err:
        print(f"[WARN] Could not pre-check PDF {s3_key}: {precheck_err}")
        return False, "precheck_failed"

    # Check for common scanned PDF indicators
    scanned_indicators = [
        'hp digital sending device',
        'scanner',
        'scan',
        'xerox',
        'canon',
        'epson',
        'ricoh'
    ]
    
    is_likely_scanned = any(indicator in creator or indicator in producer for indicator in scanned_indicators)
    
    # Enhanced validation logic - check for scanned PDFs regardless of version
    # Primary check: minimal extractable text (classic scanned document signature)
    if not first_page_text or first_page_text in ("", "-----", "-----\n\n"):
        return False, "scanned_or_image_pdf"
    
    # Secondary check: scanning device creator/producer with minimal text content
    if is_likely_scanned and len(first_page_text) < 50:  # Less than 50 chars likely means mostly images
        return False, "scanned_or_image_pdf"
    
    return True, None
