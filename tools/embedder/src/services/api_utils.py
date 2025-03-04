import requests
import os

# Types
# https://eagle-prod.apps.silver.devops.gov.bc.ca/api/public/search?pageSize=1000&dataset=List


def get_project_by_id(project_id):
    #TODO: Implement proper search from the API
    url = (
        os.environ.get("EAO_SEARCH_API_BASE_URI") 
        + f"?dataset=Project&pageNum=0&pageSize=1000&projectLegislation=default&sortBy=+name&populate=true&fields=&fuzzy=true"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        search_results = data[0]["searchResults"]
        # Filter the search results to return only the items with the matching project_id
        filtered_results = [item for item in search_results if item["_id"] == project_id]
        return filtered_results
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []


def get_projects_count() -> int:
    url = (
        os.environ.get("EAO_SEARCH_API_BASE_URI")
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
    url = (
        os.environ.get("EAO_SEARCH_API_BASE_URI")
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
    url = (
        os.environ.get("EAO_SEARCH_API_BASE_URI")
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
    url = (
        os.environ.get("EAO_SEARCH_API_BASE_URI")
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
