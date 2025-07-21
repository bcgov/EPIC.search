import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";

export interface Project {
  project_id: string;
  project_name: string;
}



const PROJECTS_CACHE_KEY = "epic_search_project_list";
const PROJECTS_CACHE_TIME_KEY = "epic_search_project_list_time";
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
  // Fetch from API
  const res = await request({ url: "/stats/processing", method: "get" });
  const projects = res.data?.result?.processing_stats?.projects || [];
  const mapped = projects.map((p: any) => ({
    project_id: p.project_id,
    project_name: p.project_name,
  }));
  // Cache in localStorage
  try {
    localStorage.setItem(PROJECTS_CACHE_KEY, JSON.stringify(mapped));
    localStorage.setItem(PROJECTS_CACHE_TIME_KEY, Date.now().toString());
  } catch (e) {
    // Ignore localStorage errors
  }
  return mapped;
};

export const useProjects = () => {
  return useQuery({
    queryKey: ["project-list"],
    queryFn: fetchProjects,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
};
