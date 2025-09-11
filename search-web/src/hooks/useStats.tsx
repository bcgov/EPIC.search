import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";
import { SummaryStatsResponse, ProcessingStatsResponse, ProjectDetailsResponse } from "@/models/Stats";

export const useStatsQuery = () => {
  return useQuery({
    queryKey: ["stats", "summary"],
    queryFn: async (): Promise<SummaryStatsResponse> => {
      const response = await request({ url: "/stats/summary", method: "GET" });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
  });
};

export const useProcessingStatsQuery = () => {
  return useQuery({
    queryKey: ["stats", "processing"],
    queryFn: async (): Promise<ProcessingStatsResponse> => {
      const response = await request({ url: "/stats/processing", method: "GET" });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
  });
};

export const useProjectDetailsQuery = (projectId: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ["stats", "project", projectId],
    queryFn: async (): Promise<ProjectDetailsResponse> => {
      const response = await request({ url: `/stats/processing/${projectId}`, method: "GET" });
      return response.data;
    },
    enabled: enabled && !!projectId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 3,
  });
};
