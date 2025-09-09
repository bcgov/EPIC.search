import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";

export interface Project {
  project_id: string;
  project_name: string;
}



const PROJECTS_CACHE_KEY = "epic_search_projects";
const PROJECTS_CACHE_TIME_KEY = "epic_search_projects_time";
const CACHE_DURATION_MS = 60 * 60 * 1000; // 60 minutes

const fetchProjects = async (): Promise<Project[]> => {
  // Try to get from localStorage first
  try {
    const cached = localStorage.getItem(PROJECTS_CACHE_KEY);
    const cachedTime = localStorage.getItem(PROJECTS_CACHE_TIME_KEY);
    if (cached && cachedTime) {
      const age = Date.now() - parseInt(cachedTime, 10);
      if (age < CACHE_DURATION_MS) {
        return JSON.parse(cached);
      }
    }
  } catch (e) {
    // Ignore localStorage errors
  }
  
  // Fetch from API with better error handling
  try {
    const res = await request({ url: "/tools/projects", method: "get" });
    const projects = res.data?.result?.projects || [];
    
    // Cache in localStorage
    try {
      localStorage.setItem(PROJECTS_CACHE_KEY, JSON.stringify(projects));
      localStorage.setItem(PROJECTS_CACHE_TIME_KEY, Date.now().toString());
    } catch (e) {
      // Ignore localStorage errors
    }
    
    return projects;
  } catch (error: any) {
    // If we have cached data and the API fails, use the cached data
    try {
      const cached = localStorage.getItem(PROJECTS_CACHE_KEY);
      if (cached) {
        console.warn('API call failed, using cached projects:', error.message);
        return JSON.parse(cached);
      }
    } catch (e) {
      // Ignore localStorage errors
    }
    
    // If no cached data available, return empty array
    console.error('Failed to fetch projects:', error.message);
    return [];
  }
};

export const useProjects = () => {
  return useQuery({
    queryKey: ["tools", "projects"],
    queryFn: fetchProjects,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 3,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: false,
  });
};
