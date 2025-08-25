"""
Tesseract OCR Processor module for extracting text from scanned PDF documents.

This module provides functionality to process scanned/image-based PDFs using
local Tesseract OCR to extract text content. It integrates with the existing PDF
validation system to handle documents that would otherwise be skipped.
"""

import fitz
import pytesseract
import io
import os

from PIL import Image
from typing import List, Dict, Any

# Import settings if available, otherwise use defaults
try:
    from src.config.settings import get_settings
    _settings_available = True
except ImportError:
    _settings_available = False


def extract_text_with_tesseract_ocr(file_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
    """
    Extract text from a scanned PDF or image file using OCR.
    
    Args:
        file_path (str): Path to the PDF or image file (supports PDF, JPG, PNG, BMP, TIFF, etc.)
        s3_key (str, optional): S3 key for logging purposes
        
    Returns:
        List[Dict[str, Any]]: List of pages with extracted text, similar to read_as_pages format
    """
    # Determine if this is an image file or PDF
    file_ext = os.path.splitext(file_path)[1].lower()
    is_image = file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif']
    
    if is_image:
        return _extract_text_from_image(file_path, s3_key)
    else:
        return _extract_text_from_pdf(file_path, s3_key)


def _extract_text_from_image(image_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
    """
    Extract text from a single image file using Tesseract OCR.
    
    Args:
        image_path (str): Path to the image file
        s3_key (str, optional): S3 key for logging purposes
        
    Returns:
        List[Dict[str, Any]]: List with single page of extracted text
    """
    # Get OCR settings if available
    if _settings_available:
        settings = get_settings()
        ocr_settings = settings.ocr_settings
        language = ocr_settings.language
    else:
        language = "eng"

    try:
        print(f"[OCR-TESSERACT] Processing image file {s3_key or image_path} using Tesseract OCR...")
        
        # Load image directly with PIL
        image = Image.open(image_path)
        
        # Extract text using Tesseract
        try:
            # Configure Tesseract for better accuracy
            # --oem 3: Use default OCR engine
            # --psm 1: Automatic page segmentation with OSD (Orientation and Script Detection)
            custom_config = f'--oem 3 --psm 1 -l {language}'
            extracted_text = pytesseract.image_to_string(image, config=custom_config)
            
            # Clean up the text
            extracted_text = extracted_text.strip()
            
            # Create page structure similar to pymupdf4llm output
            page_data = {
                "text": extracted_text,
                "page": 1,
                "metadata": {
                    "source": s3_key or image_path,
                    "page_number": 1,
                    "extraction_method": "ocr_tesseract_image",
                    "total_pages": 1,
                    "image_size": f"{image.size[0]}x{image.size[1]}",
                    "image_mode": image.mode,
                    "ocr_language": language
                }
            }
            
            pages = [page_data]
            
        except Exception as ocr_err:
            print(f"[WARN] Tesseract OCR failed for image {s3_key}: {ocr_err}")
            # Add empty page to maintain structure
            page_data = {
                "text": "",
                "page": 1,
                "metadata": {
                    "source": s3_key or image_path,
                    "page_number": 1,
                    "extraction_method": "ocr_tesseract_image_failed",
                    "total_pages": 1,
                    "error": str(ocr_err)
                }
            }
            pages = [page_data]
        
        # Log summary
        total_characters = len(pages[0].get("text", ""))
        successful_pages = 1 if pages[0].get("text", "").strip() else 0
        
        print(f"[OCR-TESSERACT] Completed OCR processing for {s3_key or image_path}:")
        print(f"[OCR-TESSERACT]   - {successful_pages}/1 image processed successfully")
        print(f"[OCR-TESSERACT]   - {total_characters} total characters extracted")
        
        return pages
        
    except Exception as e:
        print(f"[ERROR] Tesseract image OCR processing failed for {s3_key or image_path}: {e}")
        return []


def _extract_text_from_pdf(pdf_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
    """
    Extract text from a scanned PDF using OCR.
    
    Args:
        pdf_path (str): Path to the PDF file
        s3_key (str, optional): S3 key for logging purposes
        
    Returns:
        List[Dict[str, Any]]: List of pages with extracted text, similar to read_as_pages format
    """
    # Get OCR settings if available
    # Get OCR settings if available
    if _settings_available:
        settings = get_settings()
        ocr_settings = settings.ocr_settings
        dpi = ocr_settings.dpi
        language = ocr_settings.language
    else:
        dpi = 300
        language = "eng"
    
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)
        pages = []
        
        print(f"[OCR-TESSERACT] Processing scanned PDF {s3_key or pdf_path} with {doc.page_count} pages using Tesseract OCR...")
        
        try:
            for page_num in range(doc.page_count):
                try:
                    page = doc.load_page(page_num)
                
                    # Convert PDF page to image with memory safety checks
                    # Use configurable DPI for better OCR accuracy
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    
                    # Check if page is too large before processing
                    page_rect = page.rect
                    expected_width = int(page_rect.width * dpi / 72)
                    expected_height = int(page_rect.height * dpi / 72)
                    
                    # Prevent excessive memory usage (limit to ~50MB image)
                    max_pixels = 50 * 1024 * 1024  # 50MB at 4 bytes per pixel
                    if expected_width * expected_height > max_pixels:
                        print(f"[WARN] Page {page_num + 1} too large ({expected_width}x{expected_height}) - reducing DPI for safety")
                        # Calculate safer DPI
                        scale_factor = (max_pixels / (expected_width * expected_height)) ** 0.5
                        safe_dpi = max(72, int(dpi * scale_factor))
                        mat = fitz.Matrix(safe_dpi/72, safe_dpi/72)
                    
                    # Try to get pixmap with error handling
                    try:
                        pix = page.get_pixmap(matrix=mat)
                    except Exception as pix_err:
                        print(f"[WARN] Failed to create pixmap for page {page_num + 1} of {s3_key}: {pix_err}")
                        raise Exception(f"Pixmap creation failed: {pix_err}")
                    
                    # Convert to PIL Image with memory safety
                    try:
                        img_data = pix.tobytes("png")
                        if len(img_data) == 0:
                            raise Exception("Empty image data")
                        image = Image.open(io.BytesIO(img_data))
                        
                        # Verify image is valid
                        try:
                            image.verify()
                            # Re-open for processing (verify() closes the image)
                            image = Image.open(io.BytesIO(img_data))
                        except Exception as verify_err:
                            print(f"[WARN] Image verification failed for page {page_num + 1}: {verify_err}")
                            raise Exception(f"Image verification failed: {verify_err}")
                            
                    except Exception as img_err:
                        print(f"[WARN] Image conversion failed for page {page_num + 1} of {s3_key}: {img_err}")
                        pix = None  # Clean up
                        raise Exception(f"Image conversion failed: {img_err}")
                    finally:
                        # Always clean up pixmap
                        if 'pix' in locals() and pix:
                            pix = None
                    
                    # Extract text using Tesseract with timeout and memory protection
                    try:
                        # Configure Tesseract for better accuracy
                        # --oem 3: Use default OCR engine
                        # --psm 1: Automatic page segmentation with OSD (Orientation and Script Detection)
                        custom_config = f'--oem 3 --psm 1 -l {language}'
                        
                        # Add timeout to prevent hanging
                        import signal
                        import multiprocessing as mp
                        
                        def _extract_text_with_timeout(image, config, timeout=30):
                            """Extract text with timeout protection."""
                            try:
                                return pytesseract.image_to_string(image, config=config)
                            except Exception as e:
                                print(f"[WARN] Tesseract extraction failed: {e}")
                                return ""
                        
                        # Use timeout for tesseract processing
                        extracted_text = _extract_text_with_timeout(image, custom_config)
                        
                    except Exception as ocr_err:
                        print(f"[WARN] Tesseract OCR failed for page {page_num + 1} of {s3_key}: {ocr_err}")
                        extracted_text = ""
                    finally:
                        # Clean up image
                        if 'image' in locals():
                            try:
                                image.close()
                            except:
                                pass
                    
                    # Clean up the text
                    extracted_text = extracted_text.strip()
                    
                    # Create page structure similar to pymupdf4llm output
                    page_data = {
                        "text": extracted_text,
                        "page": page_num + 1,
                        "metadata": {
                            "source": s3_key or pdf_path,
                            "page_number": page_num + 1,
                            "extraction_method": "ocr_tesseract",
                            "total_pages": doc.page_count,
                            "ocr_dpi": dpi,
                            "ocr_language": language
                        }
                    }
                    
                    pages.append(page_data)
                    
                    # Log progress for large documents
                    if page_num % 10 == 0 and page_num > 0:
                        print(f"[OCR-TESSERACT] Processed {page_num + 1}/{doc.page_count} pages...")
                        
                except Exception as page_err:
                    print(f"[WARN] Complete page processing failed for page {page_num + 1} of {s3_key}: {page_err}")
                    # Add empty page to maintain structure
                    page_data = {
                        "text": "",
                        "page": page_num + 1,
                        "metadata": {
                            "source": s3_key or pdf_path,
                            "page_number": page_num + 1,
                            "extraction_method": "ocr_tesseract_failed",
                            "total_pages": doc.page_count,
                            "error": str(page_err)
                        }
                    }
                    pages.append(page_data)
                    
                    # Force garbage collection to free memory
                    import gc
                    gc.collect()
            
            # Store page count before closing document
            total_pages = doc.page_count
            
            # Log summary
            total_characters = sum(len(page.get("text", "")) for page in pages)
            successful_pages = sum(1 for page in pages if page.get("text", "").strip())
            
            print(f"[OCR-TESSERACT] Completed OCR processing for {s3_key or pdf_path}:")
            print(f"[OCR-TESSERACT]   - {successful_pages}/{total_pages} pages extracted successfully")
            print(f"[OCR-TESSERACT]   - {total_characters} total characters extracted")
            
            return pages
        finally:
            doc.close()  # Ensure the document is always closed
        
    except Exception as e:
        print(f"[ERROR] Tesseract OCR processing failed for {s3_key or pdf_path}: {e}")
        return []


def is_tesseract_available() -> bool:
    """
    Check if Tesseract OCR is available and properly configured.
    
    Returns:
        bool: True if Tesseract is available, False otherwise
    """
    # Check if OCR is disabled in settings
    if _settings_available:
        settings = get_settings()
        print(f"[DEBUG-OCR] OCR enabled in settings: {settings.ocr_settings.enabled}")
        print(f"[DEBUG-OCR] OCR provider: {settings.ocr_settings.provider}")
        print(f"[DEBUG-OCR] Tesseract path: {settings.ocr_settings.tesseract_path}")
        if not settings.ocr_settings.enabled:
            print(f"[OCR-TESSERACT] OCR processing is disabled in configuration")
            return False
        
        # Configure Tesseract path if specified
        if settings.ocr_settings.tesseract_path:
            configure_tesseract_path(settings.ocr_settings.tesseract_path)
    
    try:
        # Check what pytesseract thinks the current command is
        current_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'not set')
        print(f"[DEBUG-OCR] Current pytesseract command: {current_cmd}")
        
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        print(f"[OCR-TESSERACT] Tesseract OCR detected: version {version}")
        return True
    except Exception as e:
        print(f"[WARN] Tesseract OCR not available: {e}")
        print(f"[WARN] Install Tesseract to enable OCR processing of scanned PDFs")
        
        # Try to provide more specific error information
        current_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', 'tesseract')
        print(f"[DEBUG-OCR] pytesseract is trying to use command: {current_cmd}")
        
        # Test if the command exists
        try:
            import subprocess
            result = subprocess.run([current_cmd, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[DEBUG-OCR] Command line test SUCCESS: {result.stdout.strip()}")
                print(f"[DEBUG-OCR] This suggests a pytesseract configuration issue")
            else:
                print(f"[DEBUG-OCR] Command line test FAILED with return code {result.returncode}")
                print(f"[DEBUG-OCR] stderr: {result.stderr}")
        except FileNotFoundError:
            print(f"[DEBUG-OCR] Command not found: {current_cmd}")
        except Exception as cmd_err:
            print(f"[DEBUG-OCR] Command line test failed: {cmd_err}")
        
        # Try the full path specifically
        try:
            full_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            result = subprocess.run([full_path, '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"[DEBUG-OCR] Full path test SUCCESS: {result.stdout.strip()}")
                print(f"[DEBUG-OCR] pytesseract should be configured to use: {full_path}")
            else:
                print(f"[DEBUG-OCR] Full path test failed with return code {result.returncode}")
        except Exception as full_path_err:
            print(f"[DEBUG-OCR] Full path test failed: {full_path_err}")
        
        return False


def configure_tesseract_path(tesseract_path: str = None) -> None:
    """
    Configure the path to Tesseract executable if needed.
    
    Args:
        tesseract_path (str, optional): Path to tesseract executable
    """
    # Use path from settings if available
    if not tesseract_path and _settings_available:
        settings = get_settings()
        tesseract_path = settings.ocr_settings.tesseract_path
        print(f"[DEBUG-OCR] Got tesseract path from settings: '{tesseract_path}'")
    
    if tesseract_path and os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"[OCR-TESSERACT] Tesseract path configured: {tesseract_path}")
        return
    elif tesseract_path:
        print(f"[WARN-OCR] Specified Tesseract path does not exist: {tesseract_path}")
    
    # Common Windows paths
    if os.name == 'nt':
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', ''))
        ]
        
        print(f"[DEBUG-OCR] Checking common Tesseract paths...")
        for path in common_paths:
            print(f"[DEBUG-OCR] Checking: {path} - exists: {os.path.exists(path)}")
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"[OCR-TESSERACT] Auto-detected Tesseract path: {path}")
                return
        print(f"[WARN-OCR] No Tesseract installation found in common paths")


def initialize_tesseract_ocr() -> None:
    """
    Initialize Tesseract OCR settings and check availability.
    Should be called once at application startup.
    """
    print("[OCR-TESSERACT] Initializing Tesseract OCR processor...")
    
    # Test imports first
    try:
        import pytesseract
        print(f"[DEBUG-OCR] pytesseract imported successfully: {pytesseract.__version__ if hasattr(pytesseract, '__version__') else 'version unknown'}")
    except ImportError as e:
        print(f"[ERROR-OCR] Failed to import pytesseract: {e}")
        return
    
    try:
        from PIL import Image
        print(f"[DEBUG-OCR] PIL imported successfully")
    except ImportError as e:
        print(f"[ERROR-OCR] Failed to import PIL: {e}")
        return
    
    # Configure Tesseract path
    configure_tesseract_path()
    
    # Force set the path explicitly as a fallback
    expected_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    if os.path.exists(expected_path):
        pytesseract.pytesseract.tesseract_cmd = expected_path
        print(f"[OCR-TESSERACT] Force-configured Tesseract path: {expected_path}")
    
    # Check if OCR is available
    if is_tesseract_available():
        print("[OCR-TESSERACT] Tesseract OCR processor ready - scanned PDFs will be processed with Tesseract")
    else:
        print("[OCR-TESSERACT] Tesseract OCR processor not available - scanned PDFs will be skipped")
        print("[OCR-TESSERACT] To enable Tesseract OCR:")
        print("[OCR-TESSERACT]   1. Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
        print("[OCR-TESSERACT]   2. Set TESSERACT_PATH environment variable if needed")
        print("[OCR-TESSERACT]   3. Ensure OCR_ENABLED=true in environment")
