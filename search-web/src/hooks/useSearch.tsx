import { useMutation } from "@tanstack/react-query";
import { OnErrorType, OnSuccessType, request } from "@/utils/axiosUtils";

export type SearchStrategy = 
  | "HYBRID_SEMANTIC_FALLBACK"
  | "HYBRID_KEYWORD_FALLBACK"
  | "SEMANTIC_ONLY"
  | "KEYWORD_ONLY"
  | "HYBRID_PARALLEL"
  | "DOCUMENT_ONLY";

export interface SearchRequest {
  question: string;
  searchStrategy?: SearchStrategy;
  projectIds?: string[];
  documentTypeIds?: string[];
}

const doSearch = async (searchRequest: SearchRequest) => {
  const res = await request({
    url: "/search/query", method: "post", data: searchRequest
  });
  return res.data;
};

export const useSearchQuery = (onSuccess: OnSuccessType, onError: OnErrorType) => {
  return useMutation({
    mutationFn: doSearch,
    onSuccess,
    onError
  })
};
