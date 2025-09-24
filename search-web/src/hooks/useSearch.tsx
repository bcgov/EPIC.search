import { useMutation } from "@tanstack/react-query";
import { OnErrorType, OnSuccessType, request } from "@/utils/axiosUtils";

export type SearchStrategy = 
  | "HYBRID_SEMANTIC_FALLBACK"
  | "HYBRID_KEYWORD_FALLBACK"
  | "SEMANTIC_ONLY"
  | "KEYWORD_ONLY"
  | "HYBRID_PARALLEL"
  | "DOCUMENT_ONLY";

export interface RankingOptions {
  minScore: number;
  topN: number;
}

export type SearchMode = "rag" | "ai" | "agent" | "summary";

export interface SearchRequest {
  query: string;
  searchStrategy?: SearchStrategy;
  projectIds?: string[];
  documentTypeIds?: string[];
  ranking?: RankingOptions;
  mode?: SearchMode;
}

const doSearch = async (searchRequest: SearchRequest) => {
  try {
    const res = await request({
      url: "/search/query", 
      method: "post", 
      data: searchRequest
    });
    
    // Basic validation of response
    if (!res || !res.data) {
      throw new Error('Empty response from search API');
    }
    
    return res.data;
  } catch (error: any) {
    console.error('Search API error:', error);
    
    // Re-throw with more context if it's a network/parsing error
    if (error instanceof SyntaxError) {
      throw new Error('Invalid response format from search API');
    }
    
    if (error?.name === 'NetworkError' || error?.code === 'NETWORK_ERROR') {
      throw new Error('Network error - please check your connection');
    }
    
    throw error;
  }
};

export const useSearchQuery = (onSuccess: OnSuccessType, onError: OnErrorType) => {
  return useMutation({
    mutationFn: doSearch,
    onSuccess,
    onError
  })
};
