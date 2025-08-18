"""
File type pre-filtering utility
Checks if a file should be processed based on its S3 key without downloading
"""

import os

def get_supported_extensions():
    """Get dictionary of supported file extensions and their types"""
    return {
        # PDF files
        'pdf': 'pdf',
        
        # Image files
        'jpg': 'image',
        'jpeg': 'image', 
        'png': 'image',
        'bmp': 'image',
        'tiff': 'image',
        'tif': 'image',
        'gif': 'image',
        
        # Word documents (only DOCX, DOC is legacy and unsupported)
        'docx': 'word',
        
        # Text files
        'txt': 'text',
        'text': 'text',
        'log': 'text',
        'md': 'text',
        'markdown': 'text',
        'csv': 'text',
        'tsv': 'text',
        'rtf': 'text'
    }

def get_unsupported_extensions():
    """Get list of known unsupported file extensions that should be skipped"""
    return {
        # Legacy Office formats (not supported)
        'doc',     # Legacy Word (use DOCX instead)
        'xls',     # Excel files (not supported)
        'xlsx',    # Excel files (not supported) 
        'ppt',     # PowerPoint (not supported)
        'pptx',    # PowerPoint (not supported)
        
        # Other common file types we don't process
        'zip',     # Archives
        'rar',     # Archives
        '7z',      # Archives
        'tar',     # Archives
        'gz',      # Archives
        
        # Media files
        'mp4',     # Video
        'avi',     # Video
        'mov',     # Video
        'mp3',     # Audio
        'wav',     # Audio
        
        # Other document formats
        'odt',     # OpenDocument Text
        'ods',     # OpenDocument Spreadsheet
        'odp',     # OpenDocument Presentation
        
        # CAD/Technical files
        'dwg',     # AutoCAD
        'dxf',     # AutoCAD Exchange
        
        # Database files
        'mdb',     # Access Database
        'accdb',   # Access Database
    }

def is_file_supported(s3_key):
    """
    Check if a file should be processed based on its extension.
    
    Args:
        s3_key (str): S3 key/path of the file
        
    Returns:
        tuple: (is_supported, file_type, reason)
            is_supported (bool): True if file should be processed
            file_type (str): Type of file ('pdf', 'image', 'word', 'text', or 'unsupported')
            reason (str): Reason if not supported
    """
    if not s3_key or not isinstance(s3_key, str) or not s3_key.strip():
        return False, 'unknown', 'invalid_s3_key'
    
    # Extract file extension
    file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else ''
    
    if not file_ext:
        return False, 'unknown', 'no_file_extension'
    
    supported_extensions = get_supported_extensions()
    unsupported_extensions = get_unsupported_extensions()
    
    # Check if it's a supported type
    if file_ext in supported_extensions:
        file_type = supported_extensions[file_ext]
        return True, file_type, None
    
    # Check if it's a known unsupported type
    elif file_ext in unsupported_extensions:
        return False, 'unsupported', f'unsupported_file_type_{file_ext}'
    
    # Unknown extension
    else:
        return False, 'unknown', f'unknown_file_type_{file_ext}'

def should_skip_file_early(s3_key):
    """
    Determine if a file should be skipped before downloading from S3.
    
    Args:
        s3_key (str): S3 key/path of the file
        
    Returns:
        tuple: (should_skip, skip_reason, suggested_status)
            should_skip (bool): True if file should be skipped before download
            skip_reason (str): Reason for skipping
            suggested_status (str): Suggested processing status ('skipped' or 'failure')
    """
    is_supported, file_type, reason = is_file_supported(s3_key)
    
    if not is_supported:
        if file_type == 'unsupported':
            # Known unsupported types should be marked as "skipped" with helpful message
            file_ext = s3_key.lower().split('.')[-1] if '.' in s3_key else 'unknown'
            
            # Provide helpful guidance for common cases
            if file_ext == 'doc':
                skip_reason = f"legacy_doc_format_not_supported"
                suggestion = "Please convert DOC files to DOCX format for processing"
            elif file_ext in ['xls', 'xlsx']:
                skip_reason = f"excel_files_not_supported"
                suggestion = "Excel files are not supported for text processing"
            elif file_ext in ['ppt', 'pptx']:
                skip_reason = f"powerpoint_files_not_supported" 
                suggestion = "PowerPoint files are not supported for text processing"
            else:
                skip_reason = f"unsupported_file_type_{file_ext}"
                suggestion = f"File type '.{file_ext}' is not supported for processing"
            
            print(f"[SKIP] File {s3_key}: {suggestion}")
            return True, skip_reason, 'skipped'
        else:
            # Unknown file types - might be worth investigating
            skip_reason = reason  # 'unknown_file_type_xxx' or 'no_file_extension'
            print(f"[SKIP] File {s3_key}: Unknown or unsupported file type")
            return True, skip_reason, 'skipped'
    
    # File appears to be supported, proceed with download and validation
    return False, None, None

def get_file_type_summary():
    """Get a summary of supported and unsupported file types for documentation"""
    supported = get_supported_extensions()
    unsupported = get_unsupported_extensions()
    
    summary = {
        'supported_by_type': {},
        'unsupported_list': sorted(list(unsupported)),
        'total_supported': len(supported),
        'total_unsupported': len(unsupported)
    }
    
    # Group supported extensions by type
    for ext, file_type in supported.items():
        if file_type not in summary['supported_by_type']:
            summary['supported_by_type'][file_type] = []
        summary['supported_by_type'][file_type].append(ext)
    
    # Sort lists for consistency
    for file_type in summary['supported_by_type']:
        summary['supported_by_type'][file_type].sort()
    
    return summary
