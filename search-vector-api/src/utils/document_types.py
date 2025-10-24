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

# Document type aliases and keywords for inference
DOCUMENT_TYPE_ALIASES = {
    # 2002 Act Terms
    "5cf00c03a266b7e1877504ca": {
        "name": "Request",
        "aliases": ["request", "requests", "inquiry", "inquiries"]
    },
    "5cf00c03a266b7e1877504cb": {
        "name": "Letter", 
        "aliases": ["letter", "letters", "correspondence", "email", "emails", "memos", "memorandum", "memoranda", "communication", "communications"]
    },
    "5cf00c03a266b7e1877504cc": {
        "name": "Meeting Notes",
        "aliases": ["meeting notes", "meeting minutes", "meeting transcript", "meetings", "minutes", "transcript", "transcripts"]
    },
    "5cf00c03a266b7e1877504cd": {
        "name": "Comment Period",
        "aliases": ["comment period", "commenting period", "public comment", "submission period"]
    },
    "5cf00c03a266b7e1877504ce": {
        "name": "Plan",
        "aliases": ["management", "mitigation", "plans", "planning", "scheme"]
    },
    "5cf00c03a266b7e1877504cf": {
        "name": "Report/Study",
        "aliases": ["report", "reports", "study", "studies", "analysis", "analyses", "investigation", "investigations", "assessment", "assessments"]
    },
    "5cf00c03a266b7e1877504d0": {
        "name": "Decision Materials",
        "aliases": ["decision materials", "decision", "decisions", "ruling", "rulings", "determination", "determinations", "verdict", "verdicts"]
    },
    "5cf00c03a266b7e1877504d1": {
        "name": "Order",
        "aliases": ["orders", "directive", "directives", "instruction", "instructions", "mandate", "mandates"]
    },
    "5cf00c03a266b7e1877504d2": {
        "name": "Project Descriptions",
        "aliases": ["project description", "project descriptions", "description", "descriptions"]
    },
    "5cf00c03a266b7e1877504d3": {
        "name": "Application Information Requirement",
        "aliases": ["application information requirement", "information requirement", "requirements", "application information", "info requirement", "data requirement"]
    },
    "5cf00c03a266b7e1877504d4": {
        "name": "Application Materials",
        "aliases": ["application materials", "application", "applications", "submission", "submissions"]
    },
    "5cf00c03a266b7e1877504d5": {
        "name": "Certificate Package",
        "aliases": ["schedule b", "schedule a", "condition", "certificate package", "certificate", "certificates", "certification", "permit", "permits", "license", "licenses"]
    },
    "5cf00c03a266b7e1877504d6": {
        "name": "Exception Package",
        "aliases": ["exception package", "exception", "exceptions", "exemption", "exemptions", "variance", "variances", "waiver", "waivers"]
    },
    "5cf00c03a266b7e1877504d7": {
        "name": "Amendment Package",
        "aliases": ["condition", "amendment package", "amendment", "amendments", "modification", "modifications", "revision", "revisions"]
    },
    "5cf00c03a266b7e1877504d9": {
        "name": "Inspection Record",
        "aliases": ["inspection record", "inspection", "inspections", "audit", "audits", "reviews", "site visit", "site visits"]
    },
    "5cf00c03a266b7e1877504da": {
        "name": "Other",
        "aliases": ["other"]
    },
    "5d0d212c7d50161b92a80ee3": {
        "name": "Comment/Submission",
        "aliases": ["comment", "comments", "submission", "submissions"]
    },
    "5d0d212c7d50161b92a80ee4": {
        "name": "Tracking Table",
        "aliases": ["tracking table", "tracking", "spreadsheet", "spreadsheets", "matrix", "matrices"]
    },
    "5d0d212c7d50161b92a80ee5": {
        "name": "Scientific Memo",
        "aliases": ["scientific memo", "technical memo", "science memo", "research memo", "technical note"]
    },
    "5d0d212c7d50161b92a80ee6": {
        "name": "Agreement",
        "aliases": ["agreement", "agreements", "contract", "contracts", "accord", "accords", "treaty", "treaties", "pact", "pacts"]
    },
    
    # 2018 Act Terms
    "5df79dd77b5abbf7da6f51bd": {
        "name": "Project Description",
        "aliases": ["project description", "project descriptions", "description", "descriptions"]
    },
    "5df79dd77b5abbf7da6f51be": {
        "name": "Letter",
        "aliases": ["letter", "letters", "correspondence", "email", "emails", "memos", "memorandum", "memoranda", "communication", "communications"]
    },
    "5df79dd77b5abbf7da6f51bf": {
        "name": "Order",
        "aliases": ["orders", "directive", "directives", "instruction", "instructions", "mandate", "mandates"]
    },
    "5df79dd77b5abbf7da6f51c0": {
        "name": "Independent Memo",
        "aliases": ["independent memo", "independent note", "technical memo"]
    },
    "5df79dd77b5abbf7da6f51c1": {
        "name": "Report/Study",
        "aliases": ["report", "reports", "study", "studies", "analysis", "analyses", "investigation", "investigations", "assessment", "assessments"]
    },
    "5df79dd77b5abbf7da6f51c2": {
        "name": "Management Plan",
        "aliases": ["management plan", "operational plan"]
    },
    "5df79dd77b5abbf7da6f51c3": {
        "name": "Plan",
        "aliases": ["plans", "planning", "scheme"]
    },
    "5df79dd77b5abbf7da6f51c4": {
        "name": "Tracking Table",
        "aliases": ["tracking table", "tracking", "spreadsheet", "spreadsheets", "matrix", "matrices"]
    },
    "5df79dd77b5abbf7da6f51c5": {
        "name": "Ad/News Release",
        "aliases": ["advertisement", "advertisements", "news release", "releases", "announcement", "announcements"]
    },
    "5df79dd77b5abbf7da6f51c6": {
        "name": "Comment/Submission",
        "aliases": ["comment", "comments", "submission", "submissions"]
    },
    "5df79dd77b5abbf7da6f51c7": {
        "name": "Comment Period",
        "aliases": ["comment period", "commenting period", "public comment", "submission period"]
    },
    "5df79dd77b5abbf7da6f51c8": {
        "name": "Notification",
        "aliases": ["notification", "notifications", "advisory", "advisories"]
    },
    "5df79dd77b5abbf7da6f51c9": {
        "name": "Application Materials",
        "aliases": ["application materials", "application", "applications", "submission", "submissions"]
    },
    "5df79dd77b5abbf7da6f51ca": {
        "name": "Inspection Record",
        "aliases": ["inspection record", "inspection", "inspections", "audit", "audits", "reviews", "site visit", "site visits"]
    },
    "5df79dd77b5abbf7da6f51cb": {
        "name": "Agreement",
        "aliases": ["agreement", "agreements", "contract", "contracts", "accord", "accords", "treaty", "treaties", "pact", "pacts"]
    },
    "5df79dd77b5abbf7da6f51cc": {
        "name": "Certificate Package",
        "aliases": ["schedule b", "schedule a", "condition", "certificate package", "certificate", "certificates", "certification", "permit", "permits", "license", "licenses"]
    },
    "5df79dd77b5abbf7da6f51cd": {
        "name": "Decision Materials",
        "aliases": ["decision materials", "decision", "decisions", "ruling", "rulings", "determination", "determinations", "verdict", "verdicts"]
    },
    "5df79dd77b5abbf7da6f51ce": {
        "name": "Amendment Information",
        "aliases": ["amendment information", "amendment", "amendments", "modification", "modifications", "revision", "revisions"]
    },
    "5df79dd77b5abbf7da6f51cf": {
        "name": "Amendment Package",
        "aliases": ["condition", "amendment package", "amendment", "amendments", "modification", "modifications", "revision", "revisions"]
    },
    "5df79dd77b5abbf7da6f51d0": {
        "name": "Other",
        "aliases": ["other"]
    },
    "5dfc209bc596f00eb48b2b8e": {
        "name": "Presentation",
        "aliases": ["presentation", "presentations", "slideshow", "slideshows"]
    },
    "5dfc209bc596f00eb48b2b8f": {
        "name": "Meeting Notes",
        "aliases": ["meeting notes", "meeting minutes", "meeting transcript", "meetings", "minutes", "transcript", "transcripts"]
    },
    "5dfc209bc596f00eb48b2b90": {
        "name": "Process Order Materials",
        "aliases": ["process order materials", "process order", "procedural"]
    }
}

def get_document_type_aliases(type_id: str) -> list:
    """
    Get the aliases for a document type ID.
    
    Args:
        type_id (str): The document type ID
        
    Returns:
        list: List of alias strings for the document type
    """
    return DOCUMENT_TYPE_ALIASES.get(type_id, {}).get("aliases", [])

def get_all_document_type_aliases() -> dict:
    """
    Get all document type aliases.
    
    Returns:
        dict: Complete mapping of type IDs to their alias information
    """
    return DOCUMENT_TYPE_ALIASES.copy()
