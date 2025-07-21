import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";

export interface DocumentTypeMappingsResponse {
  result: {
    document_type_mappings: {
      [group: string]: {
        [id: string]: string;
      };
    };
  };
}


const DOC_TYPE_CACHE_KEY = "epic_search_document_type_mappings";
const DOC_TYPE_CACHE_TIME_KEY = "epic_search_document_type_mappings_time";
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
  // Fetch from API
  const response = await request({ url: "/stats/document-type-mappings", method: "GET" });
  const data = response.data;
  // Cache in localStorage
  try {
    localStorage.setItem(DOC_TYPE_CACHE_KEY, JSON.stringify(data));
    localStorage.setItem(DOC_TYPE_CACHE_TIME_KEY, Date.now().toString());
  } catch (e) {
    // Ignore localStorage errors
  }
  return data;
};

export const useDocumentTypeMappings = () => {
  return useQuery<DocumentTypeMappingsResponse>({
    queryKey: ["document-type-mappings"],
    queryFn: fetchDocumentTypeMappings,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 3,
  });
};
