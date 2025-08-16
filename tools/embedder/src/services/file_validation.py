import fitz

from .ocr.ocr_factory import extract_text_with_ocr, is_ocr_available
from PIL import Image

def validate_file(temp_path, s3_key):
    """
    Validate the file (PDF or image) for format and extractable text.
    Returns (is_valid, reason, pages_data, ocr_info) where is_valid is True if the file should be processed.
    
    This function handles both PDFs and image files:
    - PDFs: Identifies likely scanned PDFs and attempts OCR if needed
    - Images: Attempts OCR processing directly
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
    
    # Determine file type
    file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else ''
    is_pdf = file_ext == 'pdf'
    is_image = file_ext in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'gif']
    
    if is_pdf:
        return _validate_pdf_file(temp_path, s3_key, ocr_info)
    elif is_image:
        return _validate_image_file(temp_path, s3_key, ocr_info)
    else:
        print(f"[WARN] File {s3_key} is not a supported file type (PDF or image)")
        return False, "precheck_failed", None, ocr_info


def _validate_pdf_file(temp_path, s3_key, ocr_info):
    """Validate PDF file - this is the existing PDF validation logic."""
    # First, check if the file is actually a PDF
    if not s3_key.lower().endswith('.pdf'):
        print(f"[WARN] File {s3_key} is not a PDF file (invalid extension)")
        return False, "precheck_failed", None, ocr_info
    
    # Verify the file can be opened as a PDF
    try:
        test_doc = fitz.open(temp_path)
        if test_doc.page_count == 0:
            test_doc.close()
            print(f"[WARN] PDF file {s3_key} has no pages")
            return False, "precheck_failed", None, ocr_info
        test_doc.close()
    except Exception as pdf_validation_err:
        print(f"[WARN] File {s3_key} cannot be opened as a valid PDF: {pdf_validation_err}")
        return False, "precheck_failed", None, ocr_info
    
    try:
        doc = fitz.open(temp_path)
        metadata = doc.metadata
        creator = metadata.get('creator', '').lower()
        producer = metadata.get('producer', '').lower()
        first_page_text = doc[0].get_text().strip() if doc.page_count > 0 else ""
        doc.close()
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
            
            # Add OCR provider information
            try:
                from src.services.ocr.ocr_factory import OCRFactory
                provider = OCRFactory.get_provider()
                ocr_info["ocr_provider"] = provider.value
            except:
                ocr_info["ocr_provider"] = "unknown"
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
                    ocr_info["ocr_error"] = "No meaningful text extracted from OCR processing"
                    return False, "ocr_failed", None, ocr_info
            except Exception as ocr_err:
                error_msg = str(ocr_err)
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {error_msg}")
                ocr_info["ocr_error"] = error_msg
                ocr_info["ocr_error_type"] = type(ocr_err).__name__
                return False, "ocr_failed", None, ocr_info
        else:
            print(f"[SKIP] Document {s3_key} appears to be scanned but OCR is not available")
            return False, "scanned_or_image_pdf", None, ocr_info
    
    # Secondary check: scanning device creator/producer with minimal text content
    if is_likely_scanned and len(first_page_text) < 200:
        # Try OCR if available
        if is_ocr_available():
            print(f"[OCR] Document {s3_key} from scanning device with minimal text ({len(first_page_text)} chars) - attempting OCR processing...")
            ocr_info["ocr_attempted"] = True
            ocr_info["ocr_method"] = "scanning_device_minimal_text"
            
            # Add OCR provider information
            try:
                from src.services.ocr.ocr_factory import OCRFactory
                provider = OCRFactory.get_provider()
                ocr_info["ocr_provider"] = provider.value
            except:
                ocr_info["ocr_provider"] = "unknown"
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
                    ocr_info["ocr_error"] = "No meaningful text extracted from OCR processing"
                    return False, "ocr_failed", None, ocr_info
            except Exception as ocr_err:
                error_msg = str(ocr_err)
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {error_msg}")
                ocr_info["ocr_error"] = error_msg
                ocr_info["ocr_error_type"] = type(ocr_err).__name__
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
            
            # Add OCR provider information
            try:
                from src.services.ocr.ocr_factory import OCRFactory
                provider = OCRFactory.get_provider()
                ocr_info["ocr_provider"] = provider.value
            except:
                ocr_info["ocr_provider"] = "unknown"
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
                    ocr_info["ocr_error"] = "No meaningful text extracted from OCR processing"
                    # Fall through to standard processing if OCR fails
            except Exception as ocr_err:
                error_msg = str(ocr_err)
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {error_msg}")
                print(f"[INFO] Falling back to standard text extraction from {s3_key}")
                ocr_info["ocr_error"] = error_msg
                ocr_info["ocr_error_type"] = type(ocr_err).__name__
                # Fall through to standard processing if OCR fails
        else:
            print(f"[INFO] Document {s3_key} from scanning device but OCR is not available - using standard extraction")
            # Fall through to standard processing
    
    return True, None, None, ocr_info


def _validate_image_file(temp_path, s3_key, ocr_info):
    """Validate and process image file with OCR."""
    # Verify the file can be opened as an image
    try:
        test_image = Image.open(temp_path)
        image_size = test_image.size
        image_mode = test_image.mode
        test_image.close()
        print(f"[INFO] Image {s3_key} opened successfully: {image_size[0]}x{image_size[1]} pixels, mode: {image_mode}")
    except Exception as image_validation_err:
        print(f"[WARN] File {s3_key} cannot be opened as a valid image: {image_validation_err}")
        return False, "precheck_failed", None, ocr_info
    
    # For image files, always attempt OCR if available
    if is_ocr_available():
        print(f"[OCR] Image file {s3_key} - attempting OCR processing...")
        ocr_info["ocr_attempted"] = True
        ocr_info["ocr_available"] = True
        ocr_info["ocr_method"] = "image_file_processing"
        
        # Add OCR provider information
        try:
            from src.services.ocr.ocr_factory import OCRFactory
            provider = OCRFactory.get_provider()
            ocr_info["ocr_provider"] = provider.value
        except:
            ocr_info["ocr_provider"] = "unknown"
        try:
            ocr_pages = extract_text_with_ocr(temp_path, s3_key)
            if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                print(f"[OCR] Successfully extracted text from image {s3_key}")
                ocr_info["ocr_successful"] = True
                ocr_info["pages_processed"] = len(ocr_pages)
                return True, "ocr_processed", ocr_pages, ocr_info
            else:
                print(f"[OCR] OCR processing failed to extract meaningful text from image {s3_key}")
                ocr_info["pages_processed"] = len(ocr_pages) if ocr_pages else 0
                
                # Provide more specific error information based on OCR provider
                if ocr_info.get("ocr_provider") == "azure":
                    if ocr_pages and len(ocr_pages) > 0:
                        # Azure processed the file but found no text
                        ocr_info["ocr_error"] = f"Azure Document Intelligence processed {len(ocr_pages)} page(s) but detected no text content. Image may have poor quality, unusual formatting, or text that Azure cannot recognize."
                        ocr_info["azure_pages_returned"] = len(ocr_pages)
                    else:
                        # Azure returned no pages at all
                        ocr_info["ocr_error"] = "Azure Document Intelligence returned no pages. File may be corrupted or in an unsupported format."
                        ocr_info["azure_pages_returned"] = 0
                else:
                    ocr_info["ocr_error"] = "No meaningful text extracted from image OCR processing"
                
                return False, "ocr_failed", None, ocr_info
        except Exception as ocr_err:
            error_msg = str(ocr_err)
            print(f"[ERROR] OCR processing failed with exception for image {s3_key}: {error_msg}")
            ocr_info["ocr_error"] = error_msg
            ocr_info["ocr_error_type"] = type(ocr_err).__name__
            return False, "ocr_failed", None, ocr_info
    else:
        print(f"[SKIP] Image file {s3_key} requires OCR but OCR is not available")
        return False, "scanned_or_image_pdf", None, ocr_info


# Keep the original function name for backward compatibility
def validate_pdf_file(temp_path, s3_key):
    """
    Backward compatibility wrapper for validate_file.
    """
    return validate_file(temp_path, s3_key)
