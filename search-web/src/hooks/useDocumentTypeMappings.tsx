import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";

export interface DocumentTypeMappingsResponse {
  result: {
    document_types: {
      [id: string]: {
        name: string;
        aliases: string[];
        act: string;
      };
    };
    grouped_by_act: {
      [actName: string]: {
        [id: string]: string;
      };
    };
    total_types: number;
    act_2002_count: number;
    act_2018_count: number;
    metrics: {
      start_time: string;
      total_time_ms: number;
    };
  };
}


const DOC_TYPE_CACHE_KEY = "epic_search_document_types";
const DOC_TYPE_CACHE_TIME_KEY = "epic_search_document_types_time";
const CACHE_DURATION_MS = 60 * 60 * 1000; // 60 minutes

const fetchDocumentTypeMappings = async (): Promise<DocumentTypeMappingsResponse> => {
  // Try to get from localStorage first
  try {
    const cached = localStorage.getItem(DOC_TYPE_CACHE_KEY);
    const cachedTime = localStorage.getItem(DOC_TYPE_CACHE_TIME_KEY);
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
    const response = await request({ url: "/tools/document-types", method: "GET" });
    const data = response.data;
    
    // Cache in localStorage
    try {
      localStorage.setItem(DOC_TYPE_CACHE_KEY, JSON.stringify(data));
      localStorage.setItem(DOC_TYPE_CACHE_TIME_KEY, Date.now().toString());
    } catch (e) {
      // Ignore localStorage errors
    }
    
    return data;
  } catch (error: any) {
    // If we have cached data and the API fails, use the cached data
    try {
      const cached = localStorage.getItem(DOC_TYPE_CACHE_KEY);
      if (cached) {
        console.warn('API call failed, using cached document types:', error.message);
        return JSON.parse(cached);
      }
    } catch (e) {
      // Ignore localStorage errors
    }
    
    // If no cached data available, return empty structure
    console.error('Failed to fetch document types:', error.message);
    return {
      result: {
        document_types: {},
        grouped_by_act: {},
        total_types: 0,
        act_2002_count: 0,
        act_2018_count: 0,
        metrics: {
          start_time: new Date().toISOString(),
          total_time_ms: 0
        }
      }
    };
  }
};

export const useDocumentTypeMappings = (enabled: boolean = true) => {
  return useQuery<DocumentTypeMappingsResponse>({
    queryKey: ["tools", "document-types"],
    queryFn: fetchDocumentTypeMappings,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 3,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: false,
    enabled,
  });
};
