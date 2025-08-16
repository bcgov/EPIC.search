"""
Azure Document Intelligence OCR implementation for extracting text from scanned PDF documents.

This module provides functionality to process scanned/image-based PDFs using
Azure Document Intelligence (formerly Form Recognizer) services. Document Intelligence
is specifically designed for document analysis and provides superior accuracy for
text extraction from complex documents compared to Computer Vision.
"""

import os
import requests
import time
import random

from typing import List, Dict, Any

# Import settings if available, otherwise use defaults
try:
    from src.config.settings import get_settings
    _settings_available = True
except ImportError:
    _settings_available = False


def _handle_rate_limit(response, attempt: int = 1) -> int:
    """
    Handle rate limiting responses and return appropriate wait time.
    
    Args:
        response: HTTP response object
        attempt: Current attempt number
        
    Returns:
        int: Seconds to wait before retry (0 if no wait needed)
    """
    if response.status_code == 429:  # Too Many Requests
        # Check for Retry-After header
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                wait_time = int(retry_after)
                print(f"[OCR-AZURE-DI] Rate limited - waiting {wait_time} seconds (from Retry-After header)")
                return wait_time
            except ValueError:
                pass
        
        # Exponential backoff with jitter for free tier
        base_wait = min(30, 2 ** attempt)  # Cap at 30 seconds
        jitter = random.uniform(0.5, 1.5)  # Add randomness to avoid thundering herd
        wait_time = int(base_wait * jitter)
        print(f"[OCR-AZURE-DI] Rate limited - exponential backoff: waiting {wait_time} seconds (attempt {attempt})")
        return wait_time
    
    return 0


def extract_text_with_azure_ocr(file_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
    """
    Extract text from a scanned PDF or image file using Azure Document Intelligence.
    
    Args:
        file_path (str): Path to the PDF or image file (supports PDF, JPG, PNG, BMP, TIFF)
        s3_key (str, optional): S3 key for logging purposes
        
    Returns:
        List[Dict[str, Any]]: List of pages with extracted text, similar to read_as_pages format
    """
    # Get Azure Document Intelligence settings
    if _settings_available:
        settings = get_settings()
        azure_settings = settings.ocr_settings.azure_settings
        endpoint = azure_settings.endpoint
        api_key = azure_settings.api_key
        dpi = settings.ocr_settings.dpi
    else:
        endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        api_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
        dpi = 300

    if not endpoint or not api_key:
        raise ValueError("Azure Document Intelligence endpoint and API key are required")

    # Determine file type
    file_ext = os.path.splitext(file_path)[1].lower()
    is_image = file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    
    try:
        # Extract text from the file
        result = _extract_text_from_file(file_path, endpoint, api_key, s3_key, is_image)
        return result if result else []
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Azure Document Intelligence processing failed for {s3_key or file_path}: {error_msg}")
        return []


def _extract_text_from_file(
    file_path: str, 
    endpoint: str, 
    api_key: str, 
    s3_key: str = None, 
    is_image: bool = False
) -> List[Dict[str, Any]]:
    """
    Extract text from a single file using Azure Document Intelligence.
    
    Args:
        file_path (str): Path to the file to process
        endpoint (str): Azure Document Intelligence endpoint
        api_key (str): Azure Document Intelligence API key
        s3_key (str, optional): S3 key for logging purposes
        is_image (bool): Whether the file is an image
        
    Returns:
        List[Dict[str, Any]]: List of pages with extracted text
    """
    source_name = s3_key or file_path
    processing_type = "image" if is_image else "PDF"
    
    try:
        # Check file size limits (Azure Document Intelligence limits)
        file_size = os.path.getsize(file_path)
        max_size_mb = 500  # Azure Document Intelligence limit is 500MB for most tiers
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            raise Exception(f"File size ({file_size:,} bytes = {file_size/1024/1024:.1f} MB) exceeds Azure Document Intelligence limit of {max_size_mb} MB")
        
        # Log file information for debugging
        print(f"[OCR-AZURE-DI] Processing {processing_type} {source_name} using Azure Document Intelligence...")
        print(f"[OCR-AZURE-DI] File size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        
        # Read the file as bytes
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        # Extract text using Azure Document Intelligence
        extracted_pages = _call_azure_document_intelligence_api(
            file_data, endpoint, api_key, source_name, is_image
        )
        
        print(f"[OCR-AZURE-DI] Completed Azure Document Intelligence processing for {source_name}:")
        print(f"[OCR-AZURE-DI]   - {len(extracted_pages)} pages extracted")
        
        return extracted_pages
        
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Azure Document Intelligence processing failed for {source_name}: {error_msg}")
        
        # Return empty list with error information embedded
        # This allows the caller to detect the specific error
        return []


def _call_azure_document_intelligence_api(
    file_data: bytes, 
    endpoint: str, 
    api_key: str, 
    source_name: str, 
    is_image: bool = False
) -> List[Dict[str, Any]]:
    """
    Call Azure Document Intelligence API to extract text from PDF or image.
    
    Args:
        file_data (bytes): File data as bytes
        endpoint (str): Azure Document Intelligence endpoint
        api_key (str): Azure Document Intelligence API key
        source_name (str): Source file name for metadata
        is_image (bool): Whether the file is an image (affects Content-Type header)
        
    Returns:
        List[Dict[str, Any]]: List of pages with extracted text
    """
    # Choose the best API endpoint based on file type and use case
    if is_image:
        # For images, try the Read API which is optimized for text extraction
        analyze_url = f"{endpoint}/formrecognizer/documentModels/prebuilt-read:analyze"
        api_type = "Read API (optimized for image text extraction)"
    else:
        # For PDFs, use Layout API for better structure detection
        analyze_url = f"{endpoint}/formrecognizer/documentModels/prebuilt-layout:analyze"
        api_type = "Layout API (optimized for document structure)"
    
    print(f"[OCR-AZURE-DI] Using {api_type}")
    
    # Determine file type and set appropriate content type
    file_ext = os.path.splitext(source_name)[1].lower()
    
    if is_image:
        # Map file extensions to MIME types
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff'
        }
        content_type = mime_types.get(file_ext, 'image/jpeg')  # Default to JPEG
    else:
        content_type = 'application/pdf'
    
    headers = {
        'Ocp-Apim-Subscription-Key': api_key,
        'Content-Type': content_type
    }
    
    # Set parameters based on the API being used
    params = {
        'api-version': '2023-07-31'
    }
    
    # Submit file for analysis with retry logic
    file_type = "image" if is_image else "PDF"
    max_retries = 5  # Increased for free tier rate limiting
    
    # Adjust timeout based on file size (larger files need more time)
    file_size_mb = len(file_data) / (1024 * 1024)
    if file_size_mb > 10:
        upload_timeout = 120  # 2 minutes for large files
    elif file_size_mb > 5:
        upload_timeout = 60   # 1 minute for medium files
    else:
        upload_timeout = 30   # 30 seconds for small files
    
    print(f"[OCR-AZURE-DI] Using upload timeout: {upload_timeout} seconds for {file_size_mb:.1f} MB file")
    print(f"[OCR-AZURE-DI] API parameters: {params}")
    print(f"[OCR-AZURE-DI] Content-Type: {content_type}")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[OCR-AZURE-DI] Submitting {file_type} to Document Intelligence (attempt {attempt}/{max_retries})...")
            response = requests.post(analyze_url, headers=headers, params=params, data=file_data, timeout=upload_timeout)
            
            # Handle rate limiting
            if response.status_code == 429:
                wait_time = _handle_rate_limit(response, attempt)
                if attempt < max_retries:
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Rate limited after {max_retries} attempts. Try again later or upgrade to Standard tier for higher limits.")
            
            # Handle other errors
            if response.status_code == 400:
                error_details = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        error_code = error_json["error"].get("code", "BadRequest")
                        error_message = error_json["error"].get("message", error_details)
                        raise Exception(f"Bad request ({error_code}): {error_message}")
                except (ValueError, KeyError):
                    pass
                raise Exception(f"Bad request (400): File format may not be supported or file may be corrupted. Details: {error_details}")
            elif response.status_code == 401:
                raise Exception("Authentication failed (401). Check your API key.")
            elif response.status_code == 403:
                raise Exception("Access forbidden (403). Check your subscription and resource access.")
            elif response.status_code == 413:
                raise Exception("File too large (413). Azure Document Intelligence has file size limits.")
            elif response.status_code >= 500:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff for server errors
                    print(f"[OCR-AZURE-DI] Server error ({response.status_code}), retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Server error ({response.status_code}) after {max_retries} attempts")
            
            # Success case
            response.raise_for_status()
            break
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                error_msg = f"Request timeout after {upload_timeout} seconds. Large file ({file_size_mb:.1f} MB) may require longer processing time or Standard tier for better performance."
            
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"[OCR-AZURE-DI] Request failed ({error_msg}), retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Request failed after {max_retries} attempts: {error_msg}")
    
    # Get the operation ID from the response headers
    operation_url = response.headers["Operation-Location"]
    
    # Poll for results with rate limit handling
    print(f"[OCR-AZURE-DI] Waiting for Document Intelligence analysis...")
    max_attempts = 120  # Increased for free tier delays
    base_poll_interval = 3  # Start with 3 seconds for free tier
    
    for attempt in range(max_attempts):
        # Progressive polling - start fast, slow down over time
        if attempt < 10:
            poll_interval = base_poll_interval
        elif attempt < 30:
            poll_interval = 5
        else:
            poll_interval = 10
            
        time.sleep(poll_interval)
        
        try:
            result = requests.get(operation_url, headers={'Ocp-Apim-Subscription-Key': api_key}, timeout=30)
            
            # Handle rate limiting during polling
            if result.status_code == 429:
                wait_time = _handle_rate_limit(result, attempt // 10 + 1)
                time.sleep(wait_time)
                continue
                
            result.raise_for_status()
            result_json = result.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[OCR-AZURE-DI] Polling failed (attempt {attempt}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(poll_interval * 2)  # Wait longer on error
                continue
            else:
                raise Exception(f"Failed to poll results after {max_attempts} attempts: {e}")
        
        status = result_json.get("status", "unknown")
        
        if status == "succeeded":
            # Extract text from results - handle both Read API and Layout API formats
            pages = []
            if "analyzeResult" in result_json and "pages" in result_json["analyzeResult"]:
                # Determine which model was used based on the API endpoint
                model_name = "prebuilt-read" if is_image else "prebuilt-layout"
                
                for page_data in result_json["analyzeResult"]["pages"]:
                    page_num = page_data["pageNumber"]
                    
                    # Collect all text lines for this page
                    page_text_lines = []
                    if "lines" in page_data:
                        for line in page_data["lines"]:
                            page_text_lines.append(line["content"])
                    
                    # For Read API, also check for paragraphs which might have better text grouping
                    if is_image and "paragraphs" in result_json["analyzeResult"]:
                        # Read API provides paragraphs which might be better organized
                        page_paragraphs = []
                        for paragraph in result_json["analyzeResult"]["paragraphs"]:
                            # Check if this paragraph belongs to the current page
                            if paragraph.get("boundingRegions"):
                                for region in paragraph["boundingRegions"]:
                                    if region.get("pageNumber") == page_num:
                                        page_paragraphs.append(paragraph["content"])
                        
                        # If we found paragraphs, use those instead of lines for better text organization
                        if page_paragraphs:
                            page_text_lines = page_paragraphs
                            print(f"[OCR-AZURE-DI] Using {len(page_paragraphs)} paragraphs instead of {len(page_data.get('lines', []))} lines for better text organization")
                    
                    # Create page structure
                    page_info = {
                        "text": "\n".join(page_text_lines),
                        "page": page_num,
                        "metadata": {
                            "source": source_name,
                            "page_number": page_num,
                            "extraction_method": "ocr_azure_document_intelligence",
                            "total_pages": len(result_json["analyzeResult"]["pages"]),
                            "azure_model": model_name,
                            "api_type": "read" if is_image else "layout",
                            "confidence_scores": _extract_confidence_info(page_data) if "lines" in page_data else None
                        }
                    }
                    pages.append(page_info)
            
            # Log summary with detailed analysis
            total_characters = sum(len(page.get("text", "")) for page in pages)
            successful_pages = sum(1 for page in pages if page.get("text", "").strip())
            
            print(f"[OCR-AZURE-DI] Document Intelligence analysis completed:")
            print(f"[OCR-AZURE-DI]   - {successful_pages}/{len(pages)} pages extracted successfully")
            print(f"[OCR-AZURE-DI]   - {total_characters} total characters extracted")
            
            # Debug: Show what was actually extracted for troubleshooting
            if total_characters == 0:
                print(f"[OCR-AZURE-DI] DEBUG: No text extracted - analyzing response structure...")
                if "analyzeResult" in result_json:
                    analyze_result = result_json["analyzeResult"]
                    print(f"[OCR-AZURE-DI] DEBUG: analyzeResult keys: {list(analyze_result.keys())}")
                    
                    if "pages" in analyze_result:
                        print(f"[OCR-AZURE-DI] DEBUG: Found {len(analyze_result['pages'])} pages in response")
                        for i, page_data in enumerate(analyze_result["pages"]):
                            page_keys = list(page_data.keys())
                            lines_count = len(page_data.get("lines", []))
                            words_count = len(page_data.get("words", []))
                            print(f"[OCR-AZURE-DI] DEBUG: Page {i+1} keys: {page_keys}")
                            print(f"[OCR-AZURE-DI] DEBUG: Page {i+1} lines: {lines_count}, words: {words_count}")
                            
                            # Show sample of what's in lines
                            if lines_count > 0:
                                sample_lines = page_data["lines"][:3]  # First 3 lines
                                for j, line in enumerate(sample_lines):
                                    content = line.get("content", "")
                                    print(f"[OCR-AZURE-DI] DEBUG: Line {j+1}: '{content}' (length: {len(content)})")
                    
                    # For Read API, also check paragraphs
                    if is_image and "paragraphs" in analyze_result:
                        paragraphs_count = len(analyze_result["paragraphs"])
                        print(f"[OCR-AZURE-DI] DEBUG: Found {paragraphs_count} paragraphs in Read API response")
                        if paragraphs_count > 0:
                            for j, paragraph in enumerate(analyze_result["paragraphs"][:3]):  # First 3 paragraphs
                                content = paragraph.get("content", "")
                                print(f"[OCR-AZURE-DI] DEBUG: Paragraph {j+1}: '{content}' (length: {len(content)})")
                    
                    # Check for any content at all
                    if "content" in analyze_result:
                        content_length = len(analyze_result["content"])
                        print(f"[OCR-AZURE-DI] DEBUG: analyzeResult.content length: {content_length}")
                        if content_length > 0:
                            content_preview = analyze_result["content"][:200]
                            print(f"[OCR-AZURE-DI] DEBUG: Content preview: '{content_preview}'...")
                else:
                    print(f"[OCR-AZURE-DI] DEBUG: No 'analyzeResult' found in response")
                    print(f"[OCR-AZURE-DI] DEBUG: Response keys: {list(result_json.keys())}")
            
            return pages
        
        elif status == "failed":
            error_info = result_json.get("error", {})
            error_code = error_info.get("code", "UnknownError")
            error_msg = error_info.get("message", "Unknown error")
            detailed_error = f"Azure Document Intelligence analysis failed ({error_code}): {error_msg}"
            
            # Add more context for common error scenarios
            if "InvalidImage" in error_code:
                detailed_error += ". The image file may be corrupted, in an unsupported format, or too low quality for text recognition."
            elif "InvalidPdf" in error_code:
                detailed_error += ". The PDF file may be corrupted, password-protected, or in an unsupported format."
            elif "ContentLengthLimitExceeded" in error_code:
                detailed_error += ". The file exceeds Azure Document Intelligence size limits."
            elif "UnsupportedMediaType" in error_code:
                detailed_error += ". The file format is not supported by Azure Document Intelligence."
            
            raise Exception(detailed_error)
        
        # Log progress
        if attempt % 10 == 0 and attempt > 0:
            print(f"[OCR-AZURE-DI] Still processing... (attempt {attempt}/{max_attempts})")
    
    raise Exception("Azure Document Intelligence analysis timed out")


def _extract_confidence_info(page_data: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract confidence score information from Document Intelligence page data.
    
    Args:
        page_data: Page data from Document Intelligence response
        
    Returns:
        Dict with confidence statistics
    """
    if "lines" not in page_data:
        return {"average_confidence": 0.0, "min_confidence": 0.0, "max_confidence": 0.0}
    
    confidences = []
    for line in page_data["lines"]:
        if "spans" in line:
            for span in line["spans"]:
                if "confidence" in span:
                    confidences.append(span["confidence"])
    
    if not confidences:
        return {"average_confidence": 0.0, "min_confidence": 0.0, "max_confidence": 0.0}
    
    return {
        "average_confidence": sum(confidences) / len(confidences),
        "min_confidence": min(confidences),
        "max_confidence": max(confidences),
        "total_text_spans": len(confidences)
    }


def is_azure_ocr_available() -> bool:
    """
    Check if Azure Document Intelligence is available and properly configured.
    
    Returns:
        bool: True if Azure Document Intelligence is available, False otherwise
    """
    # Check if Azure OCR is disabled in settings
    if _settings_available:
        settings = get_settings()
        if not settings.ocr_settings.enabled:
            print(f"[OCR-AZURE-DI] OCR processing is disabled in configuration")
            return False
        
        azure_settings = settings.ocr_settings.azure_settings
        endpoint = azure_settings.endpoint
        api_key = azure_settings.api_key
    else:
        endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        api_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
    
    if not endpoint or not api_key:
        print(f"[WARN] Azure Document Intelligence endpoint and API key are required")
        print(f"[WARN] Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY environment variables")
        return False
    
    try:
        # Test API connectivity with retry logic for rate limits
        info_url = f"{endpoint}/formrecognizer/info"
        headers = {'Ocp-Apim-Subscription-Key': api_key}
        params = {'api-version': '2023-07-31'}
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.get(info_url, headers=headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    print(f"[OCR-AZURE-DI] Azure Document Intelligence service available")
                    return True
                elif response.status_code == 429:
                    if attempt < max_retries:
                        wait_time = _handle_rate_limit(response, attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[WARN] Azure Document Intelligence rate limited during availability check")
                        print(f"[WARN] Service may be available but currently rate limited (free tier limits)")
                        return True  # Assume available but rate limited
                else:
                    print(f"[WARN] Azure Document Intelligence API test failed: HTTP {response.status_code}")
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return False
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    print(f"[WARN] Connection attempt {attempt} failed, retrying...")
                    time.sleep(2 ** attempt)
                    continue
                else:
                    print(f"[WARN] Azure Document Intelligence not available: {e}")
                    return False
        
        return False
            
    except Exception as e:
        print(f"[WARN] Azure Document Intelligence not available: {e}")
        return False


def initialize_azure_ocr() -> None:
    """
    Initialize Azure Document Intelligence and check availability.
    """
    print("[OCR-AZURE-DI] Initializing Azure Document Intelligence...")
    
    if is_azure_ocr_available():
        print("[OCR-AZURE-DI] Azure Document Intelligence service available")
        print("[OCR-AZURE-DI] Azure Document Intelligence ready - scanned PDFs will be processed with high accuracy")
    else:
        print("[OCR-AZURE-DI] Azure Document Intelligence not available")
        print("[OCR-AZURE-DI] To enable Azure Document Intelligence:")
        print("[OCR-AZURE-DI]   1. Create an Azure Document Intelligence resource in Azure Portal")
        print("[OCR-AZURE-DI]   2. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable")
        print("[OCR-AZURE-DI]   3. Set AZURE_DOCUMENT_INTELLIGENCE_KEY environment variable")
        print("[OCR-AZURE-DI]   4. Set OCR_PROVIDER=azure in environment")
