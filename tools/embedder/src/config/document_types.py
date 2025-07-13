"""
Document Type Lookup Configuration

Maps document type IDs to human-readable names for both 2002 Act and 2018 Act terms.
Used to resolve document type metadata from API responses.
"""

# Document type mappings for both 2002 Act and 2018 Act terms
DOCUMENT_TYPE_LOOKUP = {
    # 2002 Act Terms
    "5cf00c03a266b7e1877504ca": "Request",
    "5cf00c03a266b7e1877504cb": "Letter",
    "5cf00c03a266b7e1877504cc": "Meeting Notes",
    "5cf00c03a266b7e1877504cd": "Comment Period",
    "5cf00c03a266b7e1877504ce": "Plan",
    "5cf00c03a266b7e1877504cf": "Report/Study",
    "5cf00c03a266b7e1877504d0": "Decision Materials",
    "5cf00c03a266b7e1877504d1": "Order",
    "5cf00c03a266b7e1877504d2": "Project Descriptions",
    "5cf00c03a266b7e1877504d3": "Application Information Requirement",
    "5cf00c03a266b7e1877504d4": "Application Materials",
    "5cf00c03a266b7e1877504d5": "Certificate Package",
    "5cf00c03a266b7e1877504d6": "Exception Package",
    "5cf00c03a266b7e1877504d7": "Amendment Package",
    "5cf00c03a266b7e1877504d9": "Inspection Record",
    "5cf00c03a266b7e1877504da": "Other",
    "5d0d212c7d50161b92a80ee3": "Comment/Submission",
    "5d0d212c7d50161b92a80ee4": "Tracking Table",
    "5d0d212c7d50161b92a80ee5": "Scientific Memo",
    "5d0d212c7d50161b92a80ee6": "Agreement",
    
    # 2018 Act Terms
    "5df79dd77b5abbf7da6f51bd": "Project Description",
    "5df79dd77b5abbf7da6f51be": "Letter",
    "5df79dd77b5abbf7da6f51bf": "Order",
    "5df79dd77b5abbf7da6f51c0": "Independent Memo",
    "5df79dd77b5abbf7da6f51c1": "Report/Study",
    "5df79dd77b5abbf7da6f51c2": "Management Plan",
    "5df79dd77b5abbf7da6f51c3": "Plan",
    "5df79dd77b5abbf7da6f51c4": "Tracking Table",
    "5df79dd77b5abbf7da6f51c5": "Ad/News Release",
    "5df79dd77b5abbf7da6f51c6": "Comment/Submission",
    "5df79dd77b5abbf7da6f51c7": "Comment Period",
    "5df79dd77b5abbf7da6f51c8": "Notification",
    "5df79dd77b5abbf7da6f51c9": "Application Materials",
    "5df79dd77b5abbf7da6f51ca": "Inspection Record",
    "5df79dd77b5abbf7da6f51cb": "Agreement",
    "5df79dd77b5abbf7da6f51cc": "Certificate Package",
    "5df79dd77b5abbf7da6f51cd": "Decision Materials",
    "5df79dd77b5abbf7da6f51ce": "Amendment Information",
    "5df79dd77b5abbf7da6f51cf": "Amendment Package",
    "5df79dd77b5abbf7da6f51d0": "Other",
    "5dfc209bc596f00eb48b2b8e": "Presentation",
    "5dfc209bc596f00eb48b2b8f": "Meeting Notes",
    "5dfc209bc596f00eb48b2b90": "Process Order Materials",
    
    # Unclassified
    "0000000000000000000000000": "Unclassified"
}

def get_document_type(type_id: str) -> str:
    """
    Get the human-readable document type name from a type ID.
    
    Args:
        type_id (str): The document type ID from the API
        
    Returns:
        str: Human-readable document type name, or "Unclassified" if not found
    """
    if not type_id:
        return "Unclassified"
    return DOCUMENT_TYPE_LOOKUP.get(type_id, "Unclassified")

def get_all_document_types() -> dict:
    """
    Get all document type mappings.
    
    Returns:
        dict: Complete mapping of type IDs to names
    """
    return DOCUMENT_TYPE_LOOKUP.copy()

# Create reverse lookup for human-readable names to IDs
_REVERSE_DOCUMENT_TYPE_LOOKUP = None

def _build_reverse_lookup():
    """Build reverse lookup dictionary from document type names to IDs."""
    global _REVERSE_DOCUMENT_TYPE_LOOKUP
    if _REVERSE_DOCUMENT_TYPE_LOOKUP is None:
        _REVERSE_DOCUMENT_TYPE_LOOKUP = {}
        for type_id, type_name in DOCUMENT_TYPE_LOOKUP.items():
            # Store both exact match and case-insensitive match
            _REVERSE_DOCUMENT_TYPE_LOOKUP[type_name] = type_id
            _REVERSE_DOCUMENT_TYPE_LOOKUP[type_name.lower()] = type_id
    return _REVERSE_DOCUMENT_TYPE_LOOKUP

def get_document_type_id_from_name(type_name: str) -> str:
    """
    Get the document type ID from a human-readable document type name.
    
    Args:
        type_name (str): The human-readable document type name
        
    Returns:
        str: Document type ID, or None if not found
    """
    if not type_name:
        return None
    
    reverse_lookup = _build_reverse_lookup()
    
    # Try exact match first
    if type_name in reverse_lookup:
        return reverse_lookup[type_name]
    
    # Try case-insensitive match
    if type_name.lower() in reverse_lookup:
        return reverse_lookup[type_name.lower()]
    
    return None

def resolve_document_type(type_value: str) -> tuple:
    """
    Smart document type resolution that handles both IDs and human-readable names.
    
    Args:
        type_value (str): Either a document type ID or human-readable name
        
    Returns:
        tuple: (document_type_name, document_type_id)
    """
    if not type_value:
        return "Unclassified", "0000000000000000000000000"
    
    # First, try as ID lookup (existing behavior)
    if type_value in DOCUMENT_TYPE_LOOKUP:
        return DOCUMENT_TYPE_LOOKUP[type_value], type_value
    
    # If not found as ID, try reverse lookup (type_value is human-readable name)
    type_id = get_document_type_id_from_name(type_value)
    if type_id:
        # Return the proper capitalized name from the lookup
        proper_name = DOCUMENT_TYPE_LOOKUP[type_id]
        return proper_name, type_id
    
    # If still not found, it's unclassified
    return "Unclassified", "0000000000000000000000000"
