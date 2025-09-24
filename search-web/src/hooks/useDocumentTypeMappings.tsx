import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";

export interface DocumentType {
  document_type_id: string;
  document_type_name: string;
  aliases: string[];
  act: string;
}

export interface DocumentTypeMappingsResponse {
  document_types: DocumentType[];
  total_types: number;
}

// Helper function to transform the new response to the old format for compatibility
export function transformDocumentTypesResponse(response: DocumentTypeMappingsResponse): LegacyDocumentTypeMappingsResponse {
  const grouped_by_act: { [actName: string]: { [id: string]: string } } = {};
  const document_types: { [id: string]: { name: string; aliases: string[]; act: string } } = {};
  
  let act_2002_count = 0;
  let act_2018_count = 0;
  
  response.document_types.forEach(docType => {
    // Populate the legacy document_types object
    document_types[docType.document_type_id] = {
      name: docType.document_type_name,
      aliases: docType.aliases,
      act: docType.act
    };
    
    // Group by act for the legacy grouped_by_act structure
    if (!grouped_by_act[docType.act]) {
      grouped_by_act[docType.act] = {};
    }
    grouped_by_act[docType.act][docType.document_type_id] = docType.document_type_name;
    
    // Count by act
    if (docType.act === '2002_act_terms') {
      act_2002_count++;
    } else if (docType.act === '2018_act_terms') {
      act_2018_count++;
    }
  });
  
  return {
    result: {
      document_types,
      grouped_by_act,
      total_types: response.total_types,
      act_2002_count,
      act_2018_count,
      metrics: {
        start_time: new Date().toISOString(),
        total_time_ms: 0
      }
    }
  };
}

// Legacy interface for backward compatibility
export interface LegacyDocumentTypeMappingsResponse {
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

const fetchDocumentTypeMappings = async (): Promise<LegacyDocumentTypeMappingsResponse> => {
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
    const data: DocumentTypeMappingsResponse = response.data;
    

    
    // Validate the response structure
    if (!data || !data.document_types) {
      console.warn('Invalid document types response structure:', data);
      throw new Error('Invalid response structure');
    }
    
    // Transform to legacy format for backward compatibility
    const transformedData = transformDocumentTypesResponse(data);
    
    // Cache in localStorage
    try {
      localStorage.setItem(DOC_TYPE_CACHE_KEY, JSON.stringify(transformedData));
      localStorage.setItem(DOC_TYPE_CACHE_TIME_KEY, Date.now().toString());
    } catch (e) {
      // Ignore localStorage errors
    }
    
    return transformedData;
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
    
    // If no cached data available, return empty legacy structure
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
  return useQuery<LegacyDocumentTypeMappingsResponse>({
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
