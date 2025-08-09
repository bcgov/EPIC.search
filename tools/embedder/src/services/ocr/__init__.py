"""
OCR module for processing scanned PDFs using different OCR providers.

This module provides a unified interface for different OCR implementations:
- Tesseract (local processing)
- Azure Computer Vision (cloud processing)

The OCR provider is selected via the OCR_PROVIDER environment variable.
"""

from .ocr_factory import (
    extract_text_with_ocr,
    is_ocr_available,
    initialize_ocr,
    get_ocr_info,
    OCRFactory,
    OCRProvider
)

__all__ = [
    'extract_text_with_ocr',
    'is_ocr_available', 
    'initialize_ocr',
    'get_ocr_info',
    'OCRFactory',
    'OCRProvider'
]
