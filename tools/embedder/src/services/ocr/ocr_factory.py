"""
OCR Factory module for abstracting between different OCR providers.

This module provides a unified interface to switch between different OCR 
implementations (Tesseract local, Azure Document Intelligence) based on configuration.
"""

from typing import List, Dict, Any
from enum import Enum

# Import settings if available, otherwise use defaults
try:
    from src.config.settings import get_settings
    _settings_available = True
except ImportError:
    _settings_available = False


class OCRProvider(Enum):
    """Enumeration of available OCR providers."""
    TESSERACT = "tesseract"
    AZURE = "azure"


class OCRFactory:
    """
    Factory class for creating and managing OCR implementations.
    
    Provides a unified interface to switch between different OCR providers
    based on configuration settings.
    """
    
    @staticmethod
    def get_provider() -> OCRProvider:
        """
        Get the configured OCR provider.
        
        Returns:
            OCRProvider: The configured provider
        """
        if _settings_available:
            settings = get_settings()
            provider_name = settings.ocr_settings.provider.lower()
        else:
            import os
            provider_name = os.environ.get("OCR_PROVIDER", "tesseract").lower()
        
        if provider_name == "azure":
            return OCRProvider.AZURE
        else:
            return OCRProvider.TESSERACT
    
    @staticmethod
    def extract_text_with_ocr(pdf_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
        """
        Extract text from a scanned PDF using the configured OCR provider.
        
        Args:
            pdf_path (str): Path to the PDF file
            s3_key (str, optional): S3 key for logging purposes
            
        Returns:
            List[Dict[str, Any]]: List of pages with extracted text
        """
        provider = OCRFactory.get_provider()
        
        if provider == OCRProvider.AZURE:
            from .azure_ocr_processor import extract_text_with_azure_ocr
            return extract_text_with_azure_ocr(pdf_path, s3_key)
        else:
            from .tesseract_ocr_processor import extract_text_with_tesseract_ocr
            return extract_text_with_tesseract_ocr(pdf_path, s3_key)
    
    @staticmethod
    def is_ocr_available() -> bool:
        """
        Check if the configured OCR provider is available.
        
        Returns:
            bool: True if OCR is available, False otherwise
        """
        provider = OCRFactory.get_provider()
        
        if provider == OCRProvider.AZURE:
            from .azure_ocr_processor import is_azure_ocr_available
            return is_azure_ocr_available()
        else:
            from .tesseract_ocr_processor import is_tesseract_available
            return is_tesseract_available()
    
    @staticmethod
    def initialize_ocr() -> None:
        """
        Initialize the configured OCR provider.
        """
        provider = OCRFactory.get_provider()
        
        print(f"[OCR-FACTORY] Initializing OCR with provider: {provider.value}")
        
        if provider == OCRProvider.AZURE:
            from .azure_ocr_processor import initialize_azure_ocr
            initialize_azure_ocr()
        else:
            from .tesseract_ocr_processor import initialize_tesseract_ocr
            initialize_tesseract_ocr()
    
    @staticmethod
    def get_provider_info() -> Dict[str, Any]:
        """
        Get information about the current OCR provider.
        
        Returns:
            Dict[str, Any]: Information about the provider
        """
        provider = OCRFactory.get_provider()
        available = OCRFactory.is_ocr_available()
        
        info = {
            "provider": provider.value,
            "available": available,
            "description": {
                OCRProvider.TESSERACT: "Local Tesseract OCR - Free, private, good accuracy",
                OCRProvider.AZURE: "Azure Document Intelligence - Cloud-based, excellent accuracy for documents, requires API key"
            }.get(provider, "Unknown provider")
        }
        
        if _settings_available:
            settings = get_settings()
            info["enabled"] = settings.ocr_settings.enabled
        else:
            import os
            info["enabled"] = os.environ.get("OCR_ENABLED", "true").lower() == "true"
        
        return info


# Convenience functions that delegate to the factory
def extract_text_with_ocr(pdf_path: str, s3_key: str = None) -> List[Dict[str, Any]]:
    """
    Extract text from a scanned PDF using the configured OCR provider.
    
    This is a convenience function that delegates to OCRFactory.
    """
    return OCRFactory.extract_text_with_ocr(pdf_path, s3_key)


def is_ocr_available() -> bool:
    """
    Check if OCR is available with the configured provider.
    
    This is a convenience function that delegates to OCRFactory.
    """
    return OCRFactory.is_ocr_available()


def initialize_ocr() -> None:
    """
    Initialize OCR with the configured provider.
    
    This is a convenience function that delegates to OCRFactory.
    """
    return OCRFactory.initialize_ocr()


def get_ocr_info() -> Dict[str, Any]:
    """
    Get information about the current OCR configuration.
    
    This is a convenience function that delegates to OCRFactory.
    """
    return OCRFactory.get_provider_info()
