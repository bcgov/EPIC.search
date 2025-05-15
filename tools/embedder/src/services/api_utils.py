import requests

from ..config import get_settings

"""
API Utilities module for interacting with the document search API.

This module provides functions to retrieve projects and their associated files
from the document search API. It handles pagination and error handling for API requests.
"""

settings = get_settings().document_search_settings


def get_project_by_id(project_id):
    """
    Retrieve a specific project from the API by its ID.
    
    Args:
        project_id (str): The unique identifier of the project to retrieve
        
    Returns:
        list: A list containing the project data if found, or an empty list if not found
        
    Raises:
        None: Exceptions are caught and logged, returning an empty list on failure
    """
    # Implement proper search from the API - this current just searched for all projects at 1000 page size
    url = (
        settings.document_search_url
        + f"?dataset=Project&pageNum=0&pageSize=1000&projectLegislation=default&sortBy=+name&populate=true&fields=&fuzzy=true"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        search_results = data[0]["searchResults"]
        # Filter the search results to return only the items with the matching project_id
        filtered_results = [
            item for item in search_results if item["_id"] == project_id
        ]
        return filtered_results
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []


def get_projects_count() -> int:
    """
    Get the total count of available projects in the API.
    
    Returns:
        int: The total number of projects available
        
    Raises:
        None: Exceptions are caught and logged, returning an empty list on failure
    """
    url = (
        settings.document_search_url
        + "?dataset=Project&projectLegislation=default&sortBy=+name&populate=true&fields=&fuzzy=true"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["meta"][0]["searchResultsTotal"]
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []


def get_projects(page_number=0, page_size=10):
    """
    Retrieve a paginated list of projects from the API.
    
    Args:
        page_number (int, optional): The page number to retrieve (0-indexed). Defaults to 0.
        page_size (int, optional): The number of projects per page. Defaults to 10.
        
    Returns:
        list: A list of project dictionaries, or an empty list if the request fails
        
    Raises:
        None: Exceptions are caught and logged, returning an empty list on failure
    """
    url = (
        settings.document_search_url
        + f"?dataset=Project&projectLegislation=default&sortBy=+name&populate=true&fields=&fuzzy=true&pageNum={page_number}&pageSize={page_size}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["searchResults"]
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []


def get_files_count_for_project(project_id):
    """
    Get the count of files associated with a specific project.
    
    Args:
        project_id (str): The ID of the project to count files for
        
    Returns:
        int: The number of files associated with the project
        
    Raises:
        None: Exceptions are caught and logged, returning an empty list on failure
    """
    url = (
        settings.document_search_url
        + f"?dataset=Document&project={project_id}&projectLegislation=default&sortBy=-datePosted&sortBy=+displayName&populate=true"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["meta"][0]["searchResultsTotal"]
    except requests.RequestException as e:
        print(f"Error fetching files for project {project_id}: {e}")
        return []


def get_files_for_project(project_id, page_number=0, page_size=10):
    """
    Retrieve a paginated list of files for a specific project.
    
    Args:
        project_id (str): The ID of the project to retrieve files for
        page_number (int, optional): The page number to retrieve (0-indexed). Defaults to 0.
        page_size (int, optional): The number of files per page. Defaults to 10.
        
    Returns:
        list: A list of file dictionaries, or an empty list if the request fails
        
    Raises:
        None: Exceptions are caught and logged, returning an empty list on failure
    """
    url = (
        settings.document_search_url
        + f"?dataset=Document&project={project_id}&projectLegislation=default&sortBy=-datePosted&sortBy=+displayName&populate=true&pageNum={page_number}&pageSize={page_size}"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["searchResults"]
    except requests.RequestException as e:
        print(f"Error fetching files for project {project_id}: {e}")
        return []
