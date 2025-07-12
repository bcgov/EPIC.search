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
}

def get_document_type(type_id: str) -> str:
    """
    Get the human-readable document type name from a type ID.
    
    Args:
        type_id (str): The document type ID from the API
        
    Returns:
        str: Human-readable document type name, or "Unknown" if not found
    """
    return DOCUMENT_TYPE_LOOKUP.get(type_id, "Unknown")

def get_all_document_types() -> dict:
    """
    Get all document type mappings.
    
    Returns:
        dict: Complete mapping of type IDs to names
    """
    return DOCUMENT_TYPE_LOOKUP.copy()
