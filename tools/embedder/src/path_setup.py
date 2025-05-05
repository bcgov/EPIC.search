import sys
from pathlib import Path

"""
Path Setup module for configuring Python import paths.

This module ensures that the project's root directory is available in the Python path,
allowing imports to work correctly regardless of which directory the script is run from.
It's designed to be imported and executed at the start of other modules.
"""

def setup_paths():
    """
    Add the project root directory to the Python path if it's not already there.
    
    This function ensures that modules can be imported using absolute imports
    from the project root, regardless of the current working directory.
    
    It's typically called at the beginning of modules that need to import
    from other project modules using absolute imports.
    
    Returns:
        None
    """
    # Add project root to path
    root_dir = Path(__file__).resolve().parent.parent
    if str(root_dir) not in sys.path:
        sys.path.append(str(root_dir))