import fitz
from .ocr.ocr_factory import extract_text_with_ocr, is_ocr_available
import os

def validate_pdf_file(temp_path, s3_key):
    """
    Validate the PDF file for format and extractable text.
    Returns (is_valid, reason, pages_data, ocr_info) where is_valid is True if the file should be processed.
    
    This function identifies likely scanned/image-based PDFs and attempts to process them
    using OCR if Tesseract is available. If OCR is not available, it falls back to skipping.
    """
    # Debug: Check OCR availability at the start
    ocr_available = is_ocr_available()
    print(f"[DEBUG] OCR availability check for {s3_key}: {ocr_available}")
    
    # Initialize OCR processing info for metrics
    ocr_info = {
        "ocr_available": ocr_available,
        "ocr_attempted": False,
        "ocr_successful": False,
        "ocr_method": None,
        "pages_processed": 0
    }
    
    # First, check if the file is actually a PDF
    if not s3_key.lower().endswith('.pdf'):
        print(f"[WARN] File {s3_key} is not a PDF file (invalid extension)")
        return False, "precheck_failed", None, ocr_info
    
    # Verify the file can be opened as a PDF
    try:
        test_doc = fitz.open(temp_path)
        try:
            if test_doc.page_count == 0:
                print(f"[WARN] PDF file {s3_key} has no pages")
                return False, "precheck_failed", None, ocr_info
        finally:
            test_doc.close()  # Ensure the document is always closed
    except Exception as pdf_validation_err:
        print(f"[WARN] File {s3_key} cannot be opened as a valid PDF: {pdf_validation_err}")
        return False, "precheck_failed", None, ocr_info
    
    try:
        doc = fitz.open(temp_path)
        try:
            metadata = doc.metadata
            creator = metadata.get('creator', '').lower()
            producer = metadata.get('producer', '').lower()
            first_page_text = doc[0].get_text().strip() if doc.page_count > 0 else ""
        finally:
            doc.close()  # Ensure the document is always closed
    except Exception as precheck_err:
        print(f"[WARN] Could not pre-check PDF {s3_key}: {precheck_err}")
        return False, "precheck_failed", None, ocr_info

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
        # Try OCR if available
        if is_ocr_available():
            print(f"[OCR] Document {s3_key} appears to be scanned - attempting OCR processing...")
            ocr_info["ocr_attempted"] = True
            ocr_info["ocr_method"] = "minimal_text_detection"
            try:
                ocr_pages = extract_text_with_ocr(temp_path, s3_key)
                if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                    print(f"[OCR] Successfully extracted text from scanned document {s3_key}")
                    ocr_info["ocr_successful"] = True
                    ocr_info["pages_processed"] = len(ocr_pages)
                    return True, "ocr_processed", ocr_pages, ocr_info
                else:
                    print(f"[OCR] OCR processing failed to extract meaningful text from {s3_key}")
                    ocr_info["pages_processed"] = len(ocr_pages) if ocr_pages else 0
                    return False, "ocr_failed", None, ocr_info
            except Exception as ocr_err:
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {ocr_err}")
                return False, "ocr_failed", None, ocr_info
        else:
            print(f"[SKIP] Document {s3_key} appears to be scanned but OCR is not available")
            return False, "scanned_or_image_pdf", None, ocr_info
    
    # Secondary check: scanning device creator/producer with minimal text content
    if is_likely_scanned and len(first_page_text) < 200:  # Increased threshold - even 50-200 chars might be poor extraction
        # Try OCR if available
        if is_ocr_available():
            print(f"[OCR] Document {s3_key} from scanning device with minimal text ({len(first_page_text)} chars) - attempting OCR processing...")
            ocr_info["ocr_attempted"] = True
            ocr_info["ocr_method"] = "scanning_device_minimal_text"
            try:
                ocr_pages = extract_text_with_ocr(temp_path, s3_key)
                if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                    print(f"[OCR] Successfully extracted text from scanned document {s3_key}")
                    ocr_info["ocr_successful"] = True
                    ocr_info["pages_processed"] = len(ocr_pages)
                    return True, "ocr_processed", ocr_pages, ocr_info
                else:
                    print(f"[OCR] OCR processing failed to extract meaningful text from {s3_key}")
                    ocr_info["pages_processed"] = len(ocr_pages) if ocr_pages else 0
                    return False, "ocr_failed", None, ocr_info
            except Exception as ocr_err:
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {ocr_err}")
                return False, "ocr_failed", None, ocr_info
        else:
            print(f"[SKIP] Document {s3_key} from scanning device but OCR is not available")
            return False, "scanned_or_image_pdf", None, ocr_info
    
    # Tertiary check: Known scanning devices should always get OCR treatment for better quality
    if is_likely_scanned:
        # Try OCR if available - even if there's some extracted text, OCR might be better
        if is_ocr_available():
            print(f"[OCR] Document {s3_key} from scanning device ({creator}/{producer}) - attempting OCR processing for better quality...")
            ocr_info["ocr_attempted"] = True
            ocr_info["ocr_method"] = "scanning_device_quality_improvement"
            try:
                ocr_pages = extract_text_with_ocr(temp_path, s3_key)
                if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                    print(f"[OCR] Successfully extracted text from scanned document {s3_key}")
                    ocr_info["ocr_successful"] = True
                    ocr_info["pages_processed"] = len(ocr_pages)
                    return True, "ocr_processed", ocr_pages, ocr_info
                else:
                    print(f"[OCR] OCR processing failed, falling back to standard text extraction from {s3_key}")
                    ocr_info["pages_processed"] = len(ocr_pages) if ocr_pages else 0
                    # Fall through to standard processing if OCR fails
            except Exception as ocr_err:
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {ocr_err}")
                print(f"[INFO] Falling back to standard text extraction from {s3_key}")
                # Fall through to standard processing if OCR fails
        else:
            print(f"[INFO] Document {s3_key} from scanning device but OCR is not available - using standard extraction")
            # Fall through to standard processing
    
    return True, None, None, ocr_info
