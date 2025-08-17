import fitz

from .ocr.ocr_factory import extract_text_with_ocr, is_ocr_available
from .word_reader import is_word_supported, get_word_document_metadata
from PIL import Image

def validate_file(temp_path, s3_key):
    """
    Validate the file for format and extractable text.
    Returns (is_valid, reason, pages_data, ocr_info) where is_valid is True if the file should be processed.
    
    This function handles multiple file types:
    - PDFs: Identifies likely scanned PDFs and attempts OCR if needed
    - Images: Attempts OCR processing directly  
    - Word documents: Extracts text content, with OCR fallback for legacy DOC files
    - Text files: Reads and chunks plain text content (.txt, .md, .csv, .log, .rtf, etc.)
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
    is_word = file_ext in ['docx', 'doc']
    is_text = file_ext in ['txt', 'text', 'log', 'md', 'markdown', 'csv', 'tsv', 'rtf']
    
    if is_pdf:
        return _validate_pdf_file(temp_path, s3_key, ocr_info)
    elif is_image:
        return _validate_image_file(temp_path, s3_key, ocr_info)
    elif is_word:
        return _validate_word_file(temp_path, s3_key, ocr_info)
    elif is_text:
        return _validate_text_file(temp_path, s3_key, ocr_info)
    else:
        print(f"[WARN] File {s3_key} is not a supported file type (PDF, image, Word document, or text file)")
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
    """Validate and process image file with OCR, fallback to image analysis."""
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
    
    # For image files, always attempt OCR first if available
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
                print(f"[IMAGE_ANALYSIS] Attempting image content analysis for {s3_key}...")
                # OCR failed, try image analysis
                return _try_image_analysis_fallback(temp_path, s3_key, ocr_info)
                
        except Exception as ocr_err:
            error_msg = str(ocr_err)
            print(f"[ERROR] OCR processing failed with exception for image {s3_key}: {error_msg}")
            print(f"[IMAGE_ANALYSIS] Attempting image content analysis for {s3_key}...")
            # OCR failed, try image analysis
            ocr_info["ocr_error"] = error_msg
            ocr_info["ocr_error_type"] = type(ocr_err).__name__
            return _try_image_analysis_fallback(temp_path, s3_key, ocr_info)
    else:
        print(f"[IMAGE_ANALYSIS] Image file {s3_key} - OCR not available, attempting image content analysis...")
        return _try_image_analysis_fallback(temp_path, s3_key, ocr_info)


def _try_image_analysis_fallback(temp_path, s3_key, ocr_info):
    """Try image analysis when OCR fails or is unavailable."""
    # Import image analysis
    try:
        from .image_analysis import is_image_analysis_available, analyze_image_content
    except ImportError:
        print(f"[SKIP] Image analysis not available for {s3_key}")
        return False, "image_analysis_unavailable", None, ocr_info
    
    if is_image_analysis_available():
        try:
            success, analysis_result = analyze_image_content(temp_path, s3_key)
            
            if success and analysis_result:
                print(f"[IMAGE_ANALYSIS] Successfully analyzed image content for {s3_key}")
                
                # Convert analysis result to page format for processing
                searchable_text = analysis_result.get("searchable_text", "")
                description = analysis_result.get("description", "")
                
                # Create page data structure similar to OCR/PDF pages
                page_data = [{
                    "page_number": 1,
                    "text": searchable_text,  # For backward compatibility with existing processing
                    "content": searchable_text,  # Alternative field name
                    "image_analysis": {
                        "method": analysis_result.get("method", "unknown"),
                        "description": description,
                        "tags": analysis_result.get("tags", []),
                        "objects": analysis_result.get("objects", []),
                        "categories": analysis_result.get("categories", []),
                        "confidence": analysis_result.get("confidence", 0.0)
                    },
                    "content_type": "image_with_analysis"
                }]
                
                # Add image analysis info to ocr_info for tracking
                ocr_info["image_analysis_attempted"] = True
                ocr_info["image_analysis_successful"] = True
                ocr_info["image_analysis_method"] = analysis_result.get("method", "unknown")
                ocr_info["image_analysis_confidence"] = analysis_result.get("confidence", 0.0)
                
                return True, "image_analysis_processed", page_data, ocr_info
            else:
                error_msg = analysis_result.get("error", "Unknown image analysis error") if analysis_result else "Image analysis returned no result"
                print(f"[ERROR] Image analysis failed for {s3_key}: {error_msg}")
                ocr_info["image_analysis_attempted"] = True
                ocr_info["image_analysis_successful"] = False
                ocr_info["image_analysis_error"] = error_msg
                return False, "image_analysis_failed", None, ocr_info
                
        except Exception as analysis_err:
            error_msg = str(analysis_err)
            print(f"[ERROR] Image analysis exception for {s3_key}: {error_msg}")
            ocr_info["image_analysis_attempted"] = True
            ocr_info["image_analysis_successful"] = False
            ocr_info["image_analysis_error"] = error_msg
            return False, "image_analysis_failed", None, ocr_info
    else:
        print(f"[SKIP] Image file {s3_key} - neither OCR nor image analysis available")
        return False, "no_content_analysis_available", None, ocr_info


def _validate_word_file(temp_path, s3_key, ocr_info):
    """
    Validate Word documents (DOCX/DOC) for text extraction.
    
    Args:
        temp_path: Path to the downloaded Word file
        s3_key: S3 key for identification
        ocr_info: OCR information dictionary (updated in place)
        
    Returns:
        Tuple of (is_valid, reason, pages_data, ocr_info)
    """
    print(f"[INFO] Validating Word document: {s3_key}")
    
    # Check if Word processing is available
    if not is_word_supported():
        print(f"[SKIP] Word document {s3_key} requires Word processing libraries (python-docx or docx2txt) but none are available")
        return False, "word_processing_unavailable", None, ocr_info
    
    try:
        # Get document metadata for validation
        metadata = get_word_document_metadata(temp_path)
        
        # Import here to avoid import errors if libraries aren't installed
        from .word_reader import read_word_as_pages
        
        # Try to extract text content
        pages_data = read_word_as_pages(temp_path)
        
        if not pages_data:
            print(f"[SKIP] Word document {s3_key} has no extractable content")
            return False, "no_extractable_content", None, ocr_info
        
        # Check if we have meaningful text content
        total_text = ""
        for page in pages_data:
            total_text += page.get('content', '')
        
        if len(total_text.strip()) < 10:  # Minimum meaningful content
            print(f"[SKIP] Word document {s3_key} has insufficient text content ({len(total_text)} characters)")
            return False, "insufficient_text_content", None, ocr_info
        
        # Update pages_data with metadata
        for page in pages_data:
            page['metadata'] = metadata
            page['validation_method'] = 'word_document'
        
        print(f"[SUCCESS] Word document {s3_key} validated successfully - {len(pages_data)} pages, {len(total_text)} characters")
        return True, "success", pages_data, ocr_info
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Word document validation failed: {error_msg} for {s3_key}")
        
        # Check if this is a legacy DOC file that might benefit from OCR
        file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else ''
        is_legacy_doc_error = (file_ext == 'doc' and 
                              ("Legacy DOC format" in error_msg or 
                               "word/document.xml" in error_msg or
                               "may require OCR processing" in error_msg))
        
        if is_legacy_doc_error and ocr_info.get("ocr_available", False):
            print(f"[INFO] Attempting OCR fallback for legacy DOC file: {s3_key}")
            try:
                # Convert Word document to PDF first, then apply OCR
                # This is a common approach for legacy DOC files
                import fitz  # PyMuPDF
                
                # Try to open as PDF (some DOC files can be read this way)
                try:
                    doc = fitz.open(temp_path)
                    if doc.page_count > 0:
                        print(f"[INFO] DOC file {s3_key} opened as PDF with {doc.page_count} pages, attempting OCR")
                        
                        # Use OCR on the document
                        ocr_result = extract_text_with_ocr(temp_path, s3_key)
                        doc.close()
                        
                        if ocr_result and ocr_result.get("success"):
                            ocr_info.update({
                                "ocr_attempted": True,
                                "ocr_successful": True,
                                "ocr_method": ocr_result.get("method", "unknown"),
                                "pages_processed": len(ocr_result.get("pages", []))
                            })
                            
                            pages_data = ocr_result.get("pages", [])
                            if pages_data:
                                # Add metadata to OCR pages
                                metadata = get_word_document_metadata(temp_path)
                                for page in pages_data:
                                    page['metadata'] = metadata
                                    page['validation_method'] = 'word_document_ocr'
                                
                                total_text = sum(len(page.get('content', '')) for page in pages_data)
                                print(f"[SUCCESS] Legacy DOC {s3_key} processed via OCR - {len(pages_data)} pages, {total_text} characters")
                                return True, "success", pages_data, ocr_info
                        
                        ocr_info.update({
                            "ocr_attempted": True,
                            "ocr_successful": False,
                            "ocr_method": ocr_result.get("method") if ocr_result else None
                        })
                    
                    doc.close()
                except Exception as pdf_e:
                    print(f"[INFO] Could not open DOC as PDF for {s3_key}: {pdf_e}")
                
            except Exception as ocr_e:
                print(f"[ERROR] OCR fallback failed for {s3_key}: {ocr_e}")
                ocr_info.update({
                    "ocr_attempted": True,
                    "ocr_successful": False
                })
        
        return False, "word_validation_failed", None, ocr_info


def _validate_text_file(temp_path, s3_key, ocr_info):
    """
    Validate text files for content extraction.
    
    Supports: .txt, .text, .log, .md, .markdown, .csv, .tsv, .rtf
    
    Args:
        temp_path: Path to the downloaded text file
        s3_key: S3 key for identification
        ocr_info: OCR information dictionary (updated in place)
        
    Returns:
        Tuple of (is_valid, reason, pages_data, ocr_info)
    """
    print(f"[INFO] Validating text file: {s3_key}")
    
    # Get file extension
    file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else 'txt'
    
    try:
        # Try to read the file with different encodings
        content = None
        encoding_used = None
        
        # Common encodings to try
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                with open(temp_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    encoding_used = encoding
                    break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"[WARNING] Error reading with {encoding}: {e}")
                continue
        
        if content is None:
            print(f"[ERROR] Could not decode text file {s3_key} with any common encoding")
            return False, "text_encoding_failed", None, ocr_info
        
        # Handle RTF files - strip RTF formatting codes
        if file_ext == 'rtf':
            try:
                # Basic RTF cleaning - remove RTF control words
                import re
                # Remove RTF control words (e.g., \rtf1, \ansi, etc.)
                content = re.sub(r'\\[a-z]+\d*\s?', '', content)
                # Remove braces and other RTF artifacts
                content = re.sub(r'[{}]', '', content)
                # Clean up extra whitespace
                content = re.sub(r'\s+', ' ', content)
                content = content.strip()
                print(f"[INFO] RTF file {s3_key} processed - stripped formatting codes")
            except Exception as e:
                print(f"[WARNING] RTF processing failed for {s3_key}, treating as plain text: {e}")
        
        # Check if we have meaningful content
        if len(content.strip()) < 10:
            print(f"[SKIP] Text file {s3_key} has insufficient content ({len(content.strip())} characters)")
            return False, "insufficient_text_content", None, ocr_info
        
        # Create page-like structure for compatibility with existing pipeline
        # Split long text into reasonable chunks (similar to Word document processing)
        chunk_size = 4000  # Slightly larger chunks for plain text
        
        # Split by paragraphs first (double newlines)
        paragraphs = content.split('\n\n')
        text_chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed chunk size, start new chunk
            if len(current_chunk) + len(paragraph) > chunk_size and current_chunk:
                text_chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
        
        # Add the last chunk
        if current_chunk.strip():
            text_chunks.append(current_chunk.strip())
        
        # If no chunks created (very short file), use entire content
        if not text_chunks:
            text_chunks = [content.strip()]
        
        # Create pages data structure
        pages_data = []
        for i, chunk in enumerate(text_chunks, 1):
            pages_data.append({
                'content': chunk,
                'page_number': i,
                'metadata': {
                    'file_type': 'text_file',
                    'file_extension': f'.{file_ext}',
                    'encoding': encoding_used,
                    'extraction_method': 'text_file',
                    'original_file_size': len(content)
                },
                'validation_method': 'text_file',
                'extraction_method': 'text_file'
            })
        
        total_chars = sum(len(page['content']) for page in pages_data)
        print(f"[SUCCESS] Text file {s3_key} validated successfully - {len(pages_data)} chunks, {total_chars} characters, encoding: {encoding_used}")
        return True, "success", pages_data, ocr_info
        
    except Exception as e:
        error_msg = f"Text file validation failed: {str(e)}"
        print(f"[ERROR] {error_msg} for {s3_key}")
        return False, "text_validation_failed", None, ocr_info


# Keep the original function name for backward compatibility
def validate_pdf_file(temp_path, s3_key):
    """
    Backward compatibility wrapper for validate_file.
    """
    return validate_file(temp_path, s3_key)
