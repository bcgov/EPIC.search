import fitz

from .ocr.ocr_factory import extract_text_with_ocr, is_ocr_available
from .word_reader import is_word_supported, get_word_document_metadata
from PIL import Image

def validate_file(temp_path, s3_key, max_pages=None):
    """
    Validate the file for format and extractable text.
    Returns (is_valid, reason, pages_data, ocr_info) where is_valid is True if the file should be processed.
    
    This function handles multiple file types:
    - PDFs: Identifies likely scanned PDFs and attempts OCR if needed
    - Images: Attempts OCR processing directly  
    - Word documents: Extracts text content from DOCX files. Legacy DOC files are skipped with recommendation to convert.
    - Text files: Reads and chunks plain text content (.txt, .md, .csv, .log, .rtf, etc.)
    
    Args:
        temp_path: Path to the downloaded file
        s3_key: S3 key for identification  
        max_pages: Optional maximum page count limit for PDFs
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
        return _validate_pdf_file(temp_path, s3_key, ocr_info, max_pages)
    elif is_image:
        return _validate_image_file(temp_path, s3_key, ocr_info)
    elif is_word:
        return _validate_word_file(temp_path, s3_key, ocr_info)
    elif is_text:
        return _validate_text_file(temp_path, s3_key, ocr_info)
    else:
        print(f"[WARN] File {s3_key} is not a supported file type (PDF, image, Word document, or text file)")
        return False, "precheck_failed", None, ocr_info


def _validate_pdf_file(temp_path, s3_key, ocr_info, max_pages=None):
    """Validate PDF file - this includes page count limits and content validation."""
    # First, check if the file is actually a PDF
    if not s3_key.lower().endswith('.pdf'):
        print(f"[WARN] File {s3_key} is not a PDF file (invalid extension)")
        return False, "precheck_failed", None, ocr_info
    
    # Verify the file can be opened as a PDF and get page count
    try:
        test_doc = fitz.open(temp_path)
        try:
            page_count = test_doc.page_count
            if page_count == 0:
                print(f"[WARN] PDF file {s3_key} has no pages")
                return False, "precheck_failed", None, ocr_info
        finally:
            test_doc.close()  # Ensure the document is always closed
    except Exception as pdf_validation_err:
        print(f"[WARN] File {s3_key} cannot be opened as a valid PDF: {pdf_validation_err}")
        return False, "precheck_failed", None, ocr_info
    
    # Check page count limit if specified
    if max_pages is not None and page_count > max_pages:
        print(f"[SKIP] Document {s3_key} has {page_count} pages, exceeding limit of {max_pages} pages - skipping to avoid memory/threading issues")
        return False, f"page_count_exceeded_limit_{max_pages}", None, ocr_info
    elif max_pages is not None:
        print(f"[OK] Document {s3_key} has {page_count} pages (within {max_pages} page limit)")
    
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
    
    # Check for image-based PDF indicators (PDFs created from images)
    image_pdf_indicators = [
        'adobe photoshop',
        'photoshop',
        'image converter',
        'img2pdf',
        'pil',  # Python Imaging Library
        'imagick',
        'gimp',
        'paint',
        'snagit',
        'screenshot'
    ]
    
    is_likely_scanned = any(indicator in creator or indicator in producer for indicator in scanned_indicators)
    is_likely_image_pdf = any(indicator in creator or indicator in producer for indicator in image_pdf_indicators)
    
    # Enhanced validation logic - check for scanned PDFs regardless of version
    # Primary check: minimal extractable text (classic scanned document signature)
    if not first_page_text or first_page_text in ("", "-----", "-----\n\n"):
        # Check if this appears to be an image-based PDF that should be treated as an image
        if is_likely_image_pdf:
            print(f"[IMAGE_PDF] Document {s3_key} appears to be an image-based PDF (creator: {creator}, producer: {producer}) - treating as image...")
            return _handle_image_pdf_processing(temp_path, s3_key, ocr_info)
        
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
                # Add process-level protection around OCR to prevent worker crashes
                print(f"[OCR] Starting protected OCR extraction for {s3_key}")
                
                # Use memory protection wrapper
                import gc
                
                def _safe_ocr_extraction(temp_path, s3_key):
                    """OCR extraction with memory and process protection."""
                    try:
                        # Force garbage collection before OCR
                        gc.collect()
                        
                        # Extract with error handling
                        return extract_text_with_ocr(temp_path, s3_key)
                    except MemoryError as mem_err:
                        print(f"[OCR-WARN] Memory error during OCR of {s3_key}: {mem_err}")
                        raise Exception(f"OCR memory allocation failed: {mem_err}")
                    except Exception as ocr_err:
                        print(f"[OCR-WARN] OCR extraction failed for {s3_key}: {ocr_err}")
                        raise Exception(f"OCR processing failed: {ocr_err}")
                    finally:
                        # Always clean up memory after OCR
                        gc.collect()
                
                ocr_pages = _safe_ocr_extraction(temp_path, s3_key)
                
                if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                    print(f"[OCR] Successfully extracted text from scanned document {s3_key}")
                    ocr_info["ocr_successful"] = True
                    ocr_info["pages_processed"] = len(ocr_pages)
                    return True, "ocr_processed", ocr_pages, ocr_info
                else:
                    print(f"[OCR] OCR processing failed to extract meaningful text from {s3_key}")
                    ocr_info["pages_processed"] = len(ocr_pages) if ocr_pages else 0
                    ocr_info["ocr_error"] = "No meaningful text extracted from OCR processing"
                    
                    # If OCR fails and this looks like an image PDF, try image processing
                    if is_likely_image_pdf:
                        print(f"[IMAGE_PDF] OCR failed for image-based PDF {s3_key}, trying image analysis...")
                        return _handle_image_pdf_processing(temp_path, s3_key, ocr_info)
                    
                    return False, "ocr_failed", None, ocr_info
            except Exception as ocr_err:
                error_msg = str(ocr_err)
                print(f"[ERROR] OCR processing failed with exception for {s3_key}: {error_msg}")
                ocr_info["ocr_error"] = error_msg
                ocr_info["ocr_error_type"] = type(ocr_err).__name__
                
                # If OCR fails and this looks like an image PDF, try image processing
                if is_likely_image_pdf:
                    print(f"[IMAGE_PDF] OCR failed for image-based PDF {s3_key}, trying image analysis...")
                    return _handle_image_pdf_processing(temp_path, s3_key, ocr_info)
                
                return False, "ocr_failed", None, ocr_info
        else:
            # If no OCR available but this looks like an image PDF, try image processing
            if is_likely_image_pdf:
                print(f"[IMAGE_PDF] No OCR available for image-based PDF {s3_key}, trying image analysis...")
                return _handle_image_pdf_processing(temp_path, s3_key, ocr_info)
            
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
                # Add process-level protection around OCR to prevent worker crashes
                print(f"[OCR] Starting protected OCR extraction for scanning device document {s3_key}")
                
                # Use memory protection wrapper  
                import gc
                
                def _safe_ocr_extraction(temp_path, s3_key):
                    """OCR extraction with memory and process protection."""
                    try:
                        # Force garbage collection before OCR
                        gc.collect()
                        
                        # Extract with error handling
                        return extract_text_with_ocr(temp_path, s3_key)
                    except MemoryError as mem_err:
                        print(f"[OCR-WARN] Memory error during OCR of {s3_key}: {mem_err}")
                        raise Exception(f"OCR memory allocation failed: {mem_err}")
                    except Exception as ocr_err:
                        print(f"[OCR-WARN] OCR extraction failed for {s3_key}: {ocr_err}")
                        raise Exception(f"OCR processing failed: {ocr_err}")
                    finally:
                        # Always clean up memory after OCR
                        gc.collect()
                
                ocr_pages = _safe_ocr_extraction(temp_path, s3_key)
                
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
    
    # Check for image-based PDFs with some text content
    if is_likely_image_pdf and len(first_page_text) < 500:  # Higher threshold for image PDFs
        print(f"[IMAGE_PDF] Document {s3_key} appears to be image-based PDF with minimal text ({len(first_page_text)} chars) - attempting image processing...")
        return _handle_image_pdf_processing(temp_path, s3_key, ocr_info)
    
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
                # Add process-level protection around OCR to prevent worker crashes
                print(f"[OCR] Starting protected OCR extraction for quality improvement on {s3_key}")
                
                # Use memory protection wrapper  
                import gc
                
                def _safe_ocr_extraction(temp_path, s3_key):
                    """OCR extraction with memory and process protection."""
                    try:
                        # Force garbage collection before OCR
                        gc.collect()
                        
                        # Extract with error handling
                        return extract_text_with_ocr(temp_path, s3_key)
                    except MemoryError as mem_err:
                        print(f"[OCR-WARN] Memory error during OCR of {s3_key}: {mem_err}")
                        raise Exception(f"OCR memory allocation failed: {mem_err}")
                    except Exception as ocr_err:
                        print(f"[OCR-WARN] OCR extraction failed for {s3_key}: {ocr_err}")
                        raise Exception(f"OCR processing failed: {ocr_err}")
                    finally:
                        # Always clean up memory after OCR
                        gc.collect()
                
                ocr_pages = _safe_ocr_extraction(temp_path, s3_key)
                
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


def _handle_image_pdf_processing(temp_path, s3_key, ocr_info):
    """
    Handle PDFs that are actually image files by converting them to images and processing with image analysis.
    
    Args:
        temp_path: Path to the PDF file
        s3_key: S3 key for identification
        ocr_info: OCR information dictionary (updated in place)
        
    Returns:
        Tuple of (is_valid, reason, pages_data, ocr_info)
    """
    import tempfile
    import os
    
    try:
        print(f"[IMAGE_PDF] Converting PDF {s3_key} to image for processing...")
        
        # Open the PDF and convert first page to image
        doc = fitz.open(temp_path)
        if doc.page_count == 0:
            doc.close()
            print(f"[ERROR] PDF {s3_key} has no pages")
            return False, "no_pages", None, ocr_info
        
        # Convert first page to image (high DPI for better quality)
        page = doc[0]
        mat = fitz.Matrix(300/72, 300/72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)
        
        # Save as temporary PNG file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_image:
            temp_image_path = temp_image.name
            pix.save(temp_image_path)
        
        doc.close()
        
        try:
            # First try OCR on the converted image
            if is_ocr_available():
                print(f"[IMAGE_PDF] Attempting OCR on converted image from {s3_key}...")
                ocr_info["ocr_attempted"] = True
                ocr_info["ocr_method"] = "image_pdf_conversion_ocr"
                
                # Add OCR provider information
                try:
                    from src.services.ocr.ocr_factory import OCRFactory
                    provider = OCRFactory.get_provider()
                    ocr_info["ocr_provider"] = provider.value
                except:
                    ocr_info["ocr_provider"] = "unknown"
                    
                try:
                    # Add process-level protection around OCR to prevent worker crashes
                    print(f"[IMAGE_PDF] Starting protected OCR extraction on converted image for {s3_key}")
                    
                    # Use memory protection wrapper  
                    import gc
                    
                    def _safe_ocr_extraction(temp_image_path, s3_key):
                        """OCR extraction with memory and process protection."""
                        try:
                            # Force garbage collection before OCR
                            gc.collect()
                            
                            # Extract with error handling
                            return extract_text_with_ocr(temp_image_path, s3_key)
                        except MemoryError as mem_err:
                            print(f"[OCR-WARN] Memory error during OCR of {s3_key}: {mem_err}")
                            raise Exception(f"OCR memory allocation failed: {mem_err}")
                        except Exception as ocr_err:
                            print(f"[OCR-WARN] OCR extraction failed for {s3_key}: {ocr_err}")
                            raise Exception(f"OCR processing failed: {ocr_err}")
                        finally:
                            # Always clean up memory after OCR
                            gc.collect()
                    
                    ocr_pages = _safe_ocr_extraction(temp_image_path, s3_key)
                    
                    if ocr_pages and any(page.get("text", "").strip() for page in ocr_pages):
                        print(f"[IMAGE_PDF] Successfully extracted text via OCR from image PDF {s3_key}")
                        ocr_info["ocr_successful"] = True
                        ocr_info["pages_processed"] = len(ocr_pages)
                        
                        # Update page metadata to indicate this was from an image PDF
                        for page in ocr_pages:
                            if "metadata" in page:
                                page["metadata"]["source_type"] = "image_pdf"
                                page["metadata"]["original_format"] = "pdf_converted_to_image"
                        
                        return True, "image_pdf_ocr_processed", ocr_pages, ocr_info
                    else:
                        print(f"[IMAGE_PDF] OCR failed to extract meaningful text from converted image")
                        ocr_info["ocr_error"] = "No meaningful text extracted from converted image"
                except Exception as ocr_err:
                    error_msg = str(ocr_err)
                    print(f"[ERROR] OCR failed on converted image from {s3_key}: {error_msg}")
                    ocr_info["ocr_error"] = error_msg
                    ocr_info["ocr_error_type"] = type(ocr_err).__name__
            
            # If OCR fails or is unavailable, try image analysis
            print(f"[IMAGE_PDF] Attempting image content analysis on converted image from {s3_key}...")
            
            # Import image analysis
            try:
                from .image_analysis import is_image_analysis_available, analyze_image_content
            except ImportError:
                print(f"[SKIP] Image analysis not available for {s3_key}")
                return False, "image_analysis_unavailable", None, ocr_info
            
            if is_image_analysis_available():
                try:
                    success, analysis_result = analyze_image_content(temp_image_path, s3_key)
                    
                    if success and analysis_result:
                        print(f"[IMAGE_PDF] Successfully analyzed image content for PDF {s3_key}")
                        
                        # Get PDF metadata for enhancement
                        pdf_metadata = None
                        try:
                            doc_for_metadata = fitz.open(temp_path)
                            pdf_metadata = doc_for_metadata.metadata
                            doc_for_metadata.close()
                        except:
                            pass
                        
                        # Enhance the analysis result specifically for image PDFs
                        try:
                            from .image_analysis import get_image_analysis_service
                            service = get_image_analysis_service()
                            enhanced_analysis = service.enhance_content_for_image_pdf(s3_key, analysis_result, pdf_metadata)
                            analysis_result = enhanced_analysis
                        except Exception as enhance_err:
                            print(f"[WARN] Could not enhance image PDF content for {s3_key}: {enhance_err}")
                            # Continue with original analysis result
                        
                        # Convert analysis result to page format for processing
                        searchable_text = analysis_result.get("searchable_text", "")
                        description = analysis_result.get("description", "")
                        
                        # Enhance searchable text with PDF context
                        pdf_context = f"PDF document originally created as image file (creator: {s3_key.split('/')[-1]})"
                        enhanced_searchable_text = f"{pdf_context} | {searchable_text}"
                        
                        # Extract key terms for headers and tags
                        image_tags = analysis_result.get("tags", [])
                        image_objects = analysis_result.get("objects", [])
                        image_categories = analysis_result.get("categories", [])
                        image_keywords = analysis_result.get("image_keywords", [])  # Get the new keywords
                        
                        # Create meaningful headers from image content
                        # Use the first few tags/objects as header content
                        header_content = []
                        if description:
                            header_content.append(description)
                        if image_tags:
                            header_content.extend(image_tags[:3])  # Use top 3 tags
                        if image_objects:
                            header_content.extend(image_objects[:2])  # Use top 2 objects
                        
                        # Create page data structure similar to OCR/PDF pages
                        page_metadata = {
                            "source_type": "image_pdf", 
                            "original_format": "pdf_converted_to_image",
                            "conversion_dpi": 300,
                            "extraction_method": "image_analysis_from_pdf",
                            "pdf_metadata": pdf_metadata,
                            # Add header metadata that the loader expects
                            "Header 1": header_content[0] if len(header_content) > 0 else "Image Content",
                            "Header 2": header_content[1] if len(header_content) > 1 else "",
                            "Header 3": header_content[2] if len(header_content) > 2 else "",
                            "Header 4": header_content[3] if len(header_content) > 3 else "",
                            "Header 5": header_content[4] if len(header_content) > 4 else "",
                            "Header 6": header_content[5] if len(header_content) > 5 else "",
                            # Add image analysis tags as pre-extracted tags
                            "image_tags": image_tags,
                            "image_objects": image_objects,
                            "image_categories": image_categories,
                            "image_keywords": image_keywords  # Add the comprehensive keywords for searching
                        }
                        
                        page_data = [{
                            "page_number": 1,
                            "text": enhanced_searchable_text,
                            "content": enhanced_searchable_text,
                            "image_analysis": {
                                "method": analysis_result.get("method", "unknown"),
                                "description": description,
                                "tags": image_tags,
                                "objects": image_objects,
                                "categories": image_categories,
                                "keywords": image_keywords,  # Add comprehensive keywords
                                "confidence": analysis_result.get("confidence", 0.0),
                                "pdf_enhanced": analysis_result.get("pdf_enhancement", {}).get("enhanced_for_pdf", False)
                            },
                            "metadata": page_metadata,
                            "content_type": "image_pdf_with_analysis"
                        }]
                        
                        # Add image analysis info to ocr_info for tracking
                        ocr_info["image_analysis_attempted"] = True
                        ocr_info["image_analysis_successful"] = True
                        ocr_info["image_analysis_method"] = analysis_result.get("method", "unknown")
                        ocr_info["image_analysis_confidence"] = analysis_result.get("confidence", 0.0)
                        ocr_info["pdf_converted_to_image"] = True
                        ocr_info["pdf_enhancement_applied"] = analysis_result.get("pdf_enhancement", {}).get("enhanced_for_pdf", False)
                        
                        return True, "image_pdf_analysis_processed", page_data, ocr_info
                    else:
                        error_msg = analysis_result.get("error", "Unknown image analysis error") if analysis_result else "Image analysis returned no result"
                        print(f"[ERROR] Image analysis failed for converted PDF {s3_key}: {error_msg}")
                        ocr_info["image_analysis_attempted"] = True
                        ocr_info["image_analysis_successful"] = False
                        ocr_info["image_analysis_error"] = error_msg
                        return False, "image_pdf_analysis_failed", None, ocr_info
                        
                except Exception as analysis_err:
                    error_msg = str(analysis_err)
                    print(f"[ERROR] Image analysis exception for converted PDF {s3_key}: {error_msg}")
                    ocr_info["image_analysis_attempted"] = True
                    ocr_info["image_analysis_successful"] = False
                    ocr_info["image_analysis_error"] = error_msg
                    return False, "image_pdf_analysis_failed", None, ocr_info
            else:
                print(f"[SKIP] Neither OCR nor image analysis available for image PDF {s3_key}")
                return False, "no_content_analysis_available", None, ocr_info
                
        finally:
            # Clean up temporary image file
            try:
                os.unlink(temp_image_path)
            except:
                pass  # Ignore cleanup errors
                
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Failed to process image PDF {s3_key}: {error_msg}")
        ocr_info["image_pdf_processing_error"] = error_msg
        return False, "image_pdf_processing_failed", None, ocr_info


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
            # Add process-level protection around OCR to prevent worker crashes
            print(f"[OCR] Starting protected OCR extraction on image file {s3_key}")
            
            # Use memory protection wrapper  
            import gc
            
            def _safe_ocr_extraction(temp_path, s3_key):
                """OCR extraction with memory and process protection."""
                try:
                    # Force garbage collection before OCR
                    gc.collect()
                    
                    # Extract with error handling
                    return extract_text_with_ocr(temp_path, s3_key)
                except MemoryError as mem_err:
                    print(f"[OCR-WARN] Memory error during OCR of {s3_key}: {mem_err}")
                    raise Exception(f"OCR memory allocation failed: {mem_err}")
                except Exception as ocr_err:
                    print(f"[OCR-WARN] OCR extraction failed for {s3_key}: {ocr_err}")
                    raise Exception(f"OCR processing failed: {ocr_err}")
                finally:
                    # Always clean up memory after OCR
                    gc.collect()
            
            ocr_pages = _safe_ocr_extraction(temp_path, s3_key)
            
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
                        "keywords": analysis_result.get("image_keywords", []),  # Add comprehensive keywords
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
        
        # Check if this is a legacy DOC file 
        file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else ''
        is_legacy_doc_error = (file_ext == 'doc' and 
                              ("Legacy DOC format" in error_msg or 
                               "word/document.xml" in error_msg or
                               "may require OCR processing" in error_msg or
                               "antiword" in error_msg))
        
        if is_legacy_doc_error:
            print(f"[SKIP] Legacy DOC file {s3_key} is not supported - these files require conversion to DOCX format")
            print(f"[INFO] Recommendation: Convert {s3_key} to .docx format for processing")
            return False, "legacy_doc_format_unsupported", None, ocr_info
        
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
def validate_pdf_file(temp_path, s3_key, max_pages=None):
    """
    Backward compatibility wrapper for validate_file.
    """
    return validate_file(temp_path, s3_key, max_pages)
