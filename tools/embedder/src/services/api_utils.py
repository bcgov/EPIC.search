import requests
import os

def get_projects():
    url = os.environ.get("EAO_SEARCH_API_BASE_URI") + "?dataset=Project&projectLegislation=default&sortBy=+name&populate=true&fields=&fuzzy=true"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["searchResults"]
    except requests.RequestException as e:
        print(f"Error fetching projects: {e}")
        return []

def get_files_for_project(project_id):
    url = os.environ.get("EAO_SEARCH_API_BASE_URI") + f"?dataset=Document&project={project_id}&projectLegislation=default&sortBy=-datePosted&sortBy=+displayName&populate=true"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data[0]["searchResults"] 
    except requests.RequestException as e:
        print(f"Error fetching files for project {project_id}: {e}")
        return []
