import { useQuery } from "@tanstack/react-query";
import { request } from "@/utils/axiosUtils";
import { SearchStrategy } from "@/hooks/useSearch";

export interface SearchStrategyOption {
  value: SearchStrategy | undefined;
  label: string;
  description: string;
  enabled?: boolean;
}

export interface SearchStrategiesResponse {
  result: {
    strategies: {
      [key: string]: {
        name: string;
        description: string;
        enabled: boolean;
      };
    };
    default_strategy: string;
    metrics: {
      start_time: string;
      total_time_ms: number;
    };
  };
}

const STRATEGIES_CACHE_KEY = "epic_search_strategies";
const STRATEGIES_CACHE_TIME_KEY = "epic_search_strategies_time";
const CACHE_DURATION_MS = 60 * 60 * 1000; // 60 minutes

const fetchSearchStrategies = async (): Promise<SearchStrategyOption[]> => {
  // Try to get from localStorage first
  try {
    const cached = localStorage.getItem(STRATEGIES_CACHE_KEY);
    const cachedTime = localStorage.getItem(STRATEGIES_CACHE_TIME_KEY);
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
    const response = await request({ url: "/tools/search-strategies", method: "GET" });
    const data = response.data;
    
    // Transform API response to match our SearchStrategyOption interface
    const strategies: SearchStrategyOption[] = [
      {
        value: undefined,
        label: "Default",
        description: `Use the default search strategy (${data.result?.default_strategy || 'HYBRID_SEMANTIC_FALLBACK'})`,
        enabled: true
      }
    ];
    
    // Check if we have the expected structure
    if (data.result?.strategies) {
      // Add each strategy from the API
      Object.entries(data.result.strategies).forEach(([key, strategy]: [string, any]) => {
        if (strategy.enabled !== false) { // Default to enabled if not specified
          strategies.push({
            value: strategy.name as SearchStrategy, // Use the name as the value, not the key
            label: strategy.name || key,
            description: strategy.description || `${strategy.name || key} search strategy`,
            enabled: strategy.enabled !== false
          });
        }
      });
    } else {
      console.warn('API response does not have expected structure:', data);
    }
    
    // Cache in localStorage
    try {
      localStorage.setItem(STRATEGIES_CACHE_KEY, JSON.stringify(strategies));
      localStorage.setItem(STRATEGIES_CACHE_TIME_KEY, Date.now().toString());
    } catch (e) {
      // Ignore localStorage errors
    }
    
    return strategies;
  } catch (error: any) {
    // If we have cached data and the API fails, use the cached data
    try {
      const cached = localStorage.getItem(STRATEGIES_CACHE_KEY);
      if (cached) {
        console.warn('API call failed, using cached search strategies:', error.message);
        return JSON.parse(cached);
      }
    } catch (e) {
      // Ignore localStorage errors
    }
    
    // If no cached data available, return fallback strategies
    console.error('Failed to fetch search strategies, using fallback:', error.message);
    return [
      {
        value: undefined,
        label: "Default",
        description: "Use the default search strategy",
        enabled: true
      },
      {
        value: "HYBRID_SEMANTIC_FALLBACK" as SearchStrategy,
        label: "Hybrid Semantic Fallback",
        description: "Document keyword filter → Semantic search → Keyword fallback",
        enabled: true
      },
      {
        value: "SEMANTIC_ONLY" as SearchStrategy,
        label: "Semantic Only",
        description: "Pure semantic search without keyword filtering",
        enabled: true
      },
      {
        value: "KEYWORD_ONLY" as SearchStrategy,
        label: "Keyword Only",
        description: "Pure keyword search without semantic components",
        enabled: true
      }
    ];
  }
};

export const useSearchStrategies = (enabled: boolean = true) => {
  return useQuery<SearchStrategyOption[]>({
    queryKey: ["tools", "search-strategies"],
    queryFn: fetchSearchStrategies,
    staleTime: 60 * 60 * 1000, // 1 hour
    retry: 3,
    refetchOnWindowFocus: false,
    refetchOnMount: false,
    refetchInterval: false,
    enabled,
  });
};
