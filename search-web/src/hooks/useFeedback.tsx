import { useMutation } from "@tanstack/react-query";
import { OnErrorType, OnSuccessType, request } from "@/utils/axiosUtils";

export type FeedbackValue = "useful" | "not_useful" | "neutral";

export interface FeedbackRequest {
  sessionId?: string;
  queryText?: string;
  projectIds?: string[];
  documentTypeIds?: string[];
  feedback?: FeedbackValue;
  comments?: string;
}

export interface FeedbackResponse {
  sessionId?: string;
  message?: string;
}

// Function that calls your API
const submitFeedback = async (payload: FeedbackRequest) => {
  try {
    const method = "patch";

    const res = await request({
      url: "/search/feedback",
      method,
      data: payload,
    });

    if (!res || !res.data) {
        throw new Error("Empty response from feedback API");
    }

    return res.data;
  } catch (error: any) {
    console.error('Feedback API error:', error);
    
    // Re-throw with more context if it's a network/parsing error
    if (error instanceof SyntaxError) {
      throw new Error('Invalid response format from feedback API');
    }
    
    if (error?.name === 'NetworkError' || error?.code === 'NETWORK_ERROR') {
      throw new Error('Network error - please check your connection');
    }
    
    throw error;
  }
};

export const useFeedback = (onSuccess: OnSuccessType, onError: OnErrorType) => {
  return useMutation({
    mutationFn: submitFeedback,
    onSuccess,
    onError
  })
};
