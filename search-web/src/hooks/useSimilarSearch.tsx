import { useMutation } from "@tanstack/react-query";
import { request as apiRequest } from "@/utils/axiosUtils";
import { SimilarSearchRequest, SimilarSearchResponse } from "@/models/Search";

export const useSimilarSearch = () => {
  return useMutation({
    mutationFn: async (requestData: SimilarSearchRequest): Promise<SimilarSearchResponse> => {
      const response = await apiRequest({
        method: "POST",
        url: "/search/similar",
        data: requestData,
      });
      return response.data;
    },
  });
};
