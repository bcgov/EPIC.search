# Import and run path setup
from src.path_setup import setup_paths
setup_paths()

from src.config.settings import get_settings
settings = get_settings()

"""
Keyword Extraction Factory/Controller

This module provides a centralized interface for selecting and executing
the appropriate keyword extraction implementation based on configuration settings.

Supported Modes:
- standard: Full KeyBERT with highest quality (slower)
- fast: Optimized KeyBERT with good quality (5-10x faster)  
- simplified: Enhanced TF-IDF with custom features (fastest, 30-60x faster)

Usage:
    from src.services.keywords.keyword_factory import extract_keywords_from_chunks
    chunks_with_keywords, all_keywords = extract_keywords_from_chunks(chunk_dicts, document_id)
"""

from typing import List, Dict, Set, Tuple, Any
import time
import logging

# Import all extraction implementations
from src.services.keywords.keyword_extractor_standard import extract_keywords_from_chunks_standard
from src.services.keywords.keyword_extractor_fast import extract_keywords_from_chunks_fast
from src.services.keywords.keyword_extractor_simplified import extract_keywords_from_chunks_simplified

logger = logging.getLogger(__name__)

# Mode mapping for extraction functions
EXTRACTION_MODES = {
    'standard': extract_keywords_from_chunks_standard,
    'fast': extract_keywords_from_chunks_fast,
    'simplified': extract_keywords_from_chunks_simplified
}

def extract_keywords_from_chunks(
    chunk_dicts: List[Dict[str, Any]], 
    document_id: str = None
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Factory function to extract keywords using the configured extraction mode.
    
    This function automatically selects the appropriate keyword extraction
    implementation based on the KEYWORD_EXTRACTION_MODE environment variable.
    
    Args:
        chunk_dicts (List[Dict]): List of chunk dictionaries with 'content' and 'metadata' fields
        document_id (str, optional): Identifier for the document being processed (for logging)
        
    Returns:
        Tuple[List[Dict], Set[str]]: (updated_chunk_dicts_with_keywords, set_of_all_unique_keywords)
        
    Raises:
        ValueError: If the configured extraction mode is not supported
        
    Example:
        chunks = [
            {"content": "Sample text", "metadata": {}},
            {"content": "More text", "metadata": {}}
        ]
        updated_chunks, all_keywords = extract_keywords_from_chunks(chunks, "doc_123")
    """
    extraction_mode = settings.multi_processing_settings.keyword_extraction_mode.lower()
    
    # Validate extraction mode
    if extraction_mode not in EXTRACTION_MODES:
        available_modes = ', '.join(EXTRACTION_MODES.keys())
        error_msg = f"Unsupported keyword extraction mode '{extraction_mode}'. Available modes: {available_modes}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Get the extraction function for the configured mode
    extraction_function = EXTRACTION_MODES[extraction_mode]
    
    # Log the mode being used
    doc_log_id = "unknown"
    if document_id:
        import os
        doc_log_id = os.path.basename(document_id)
        if len(doc_log_id) > 30:
            doc_log_id = doc_log_id[:27] + "..."
    
    logger.info(f"[KEYWORD-FACTORY] [{doc_log_id}] Using extraction mode: {extraction_mode}")
    
    # Execute keyword extraction with timing
    start_time = time.time()
    try:
        result = extraction_function(chunk_dicts, document_id)
        execution_time = time.time() - start_time
        
        # Log successful extraction
        chunk_count = len(chunk_dicts) if chunk_dicts else 0
        keyword_count = len(result[1]) if len(result) > 1 else 0
        logger.info(f"[KEYWORD-FACTORY] [{doc_log_id}] Extraction completed in {execution_time:.3f}s "
                   f"({chunk_count} chunks, {keyword_count} unique keywords)")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"[KEYWORD-FACTORY] [{doc_log_id}] Extraction failed after {execution_time:.3f}s: {str(e)}")
        raise

def get_extraction_mode_info() -> Dict[str, Any]:
    """
    Get information about the currently configured extraction mode.
    
    Returns:
        Dict: Information about the current mode including name, description, and performance characteristics
    """
    extraction_mode = settings.multi_processing_settings.keyword_extraction_mode.lower()
    
    mode_info = {
        'standard': {
            'name': 'Standard KeyBERT',
            'description': 'Full KeyBERT implementation with highest semantic quality',
            'performance': 'Slowest (baseline)',
            'quality': 'Highest',
            'best_for': 'Offline processing where quality is paramount'
        },
        'fast': {
            'name': 'Optimized KeyBERT',
            'description': 'Optimized KeyBERT with reduced parameters for faster processing',
            'performance': '5-10x faster than standard',
            'quality': 'High',
            'best_for': 'Real-time processing where KeyBERT quality is preferred'
        },
        'simplified': {
            'name': 'Enhanced TF-IDF',
            'description': 'Custom TF-IDF implementation with domain-specific enhancements',
            'performance': '30-60x faster than standard',
            'quality': 'Good (domain-optimized)',
            'best_for': 'High-volume processing where speed is critical'
        }
    }
    
    current_info = mode_info.get(extraction_mode, {
        'name': 'Unknown',
        'description': f'Unknown mode: {extraction_mode}',
        'performance': 'Unknown',
        'quality': 'Unknown',
        'best_for': 'Unknown'
    })
    
    current_info['current_mode'] = extraction_mode
    return current_info

def validate_extraction_mode(mode: str) -> bool:
    """
    Validate if the given extraction mode is supported.
    
    Args:
        mode (str): The extraction mode to validate
        
    Returns:
        bool: True if the mode is supported, False otherwise
    """
    return mode.lower() in EXTRACTION_MODES

def list_available_modes() -> List[str]:
    """
    Get a list of all available extraction modes.
    
    Returns:
        List[str]: List of available extraction mode names
    """
    return list(EXTRACTION_MODES.keys())

# Backward compatibility - export the main function with original name
extract_keywords_from_chunks_factory = extract_keywords_from_chunks
