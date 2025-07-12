import { useMutation } from "@tanstack/react-query";
import { OnErrorType, OnSuccessType, request } from "@/utils/axiosUtils";

const doSearch = async (searchText: string) => {
  const res = await request({
    url: "/search/query", method: "post", data: {
      question: searchText
    }
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
