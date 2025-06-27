import fitz

def validate_pdf_file(temp_path, s3_key):
    """
    Validate the PDF file for format and extractable text.
    Returns (is_valid, reason) where is_valid is True if the file should be processed.
    """
    try:
        doc = fitz.open(temp_path)
        pdf_version = doc.metadata['format']
        first_page_text = doc[0].get_text().strip() if doc.page_count > 0 else ""
        doc.close()
    except Exception as precheck_err:
        print(f"[WARN] Could not pre-check PDF {s3_key}: {precheck_err}")
        return False, "precheck_failed"

    if pdf_version == "PDF 1.4" and (not first_page_text or first_page_text in ("", "-----", "-----\n\n")):
        return False, "scanned_or_image_pdf"
    return True, None
