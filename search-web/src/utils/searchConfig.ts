import { SearchStrategy, SearchMode } from "@/hooks/useSearch";

const SEARCH_STRATEGY_KEY = "epic-search-strategy";
const RANKING_CONFIG_KEY = "epic-ranking-config";
const SEARCH_MODE_KEY = "epic-search-mode";

export interface RankingConfig {
  useCustomRanking: boolean;
  scoreSetting: 'STRICT' | 'MODERATE' | 'FLEXIBLE' | 'VERY_FLEXIBLE';
  resultsSetting: 'FEW' | 'MEDIUM' | 'MANY' | 'MAXIMUM';
}

// Score setting mappings (lower = more restrictive)
export const scoreSettings = {
  'STRICT': 0,
  'MODERATE': -3,
  'FLEXIBLE': -6,
  'VERY_FLEXIBLE': -12
};

// Results setting mappings
export const resultsSettings = {
  'FEW': 5,
  'MEDIUM': 15,
  'MANY': 50,
  'MAXIMUM': 100
};

export const getStoredRankingConfig = (): RankingConfig => {
  try {
    const stored = localStorage.getItem(RANKING_CONFIG_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    console.warn("Failed to read ranking config from localStorage:", error);
  }
  return {
    useCustomRanking: false,
    scoreSetting: 'FLEXIBLE',
    resultsSetting: 'MEDIUM'
  };
};

export const setStoredRankingConfig = (config: RankingConfig): void => {
  try {
    localStorage.setItem(RANKING_CONFIG_KEY, JSON.stringify(config));
  } catch (error) {
    console.warn("Failed to store ranking config in localStorage:", error);
  }
};

export const getStoredSearchStrategy = (): SearchStrategy | undefined => {
  try {
    const stored = localStorage.getItem(SEARCH_STRATEGY_KEY);
    if (stored) {
      return stored as SearchStrategy;
    }
  } catch (error) {
    console.warn("Failed to read search strategy from localStorage:", error);
  }
  return undefined;
};

export const setStoredSearchStrategy = (strategy: SearchStrategy | undefined): void => {
  try {
    if (strategy) {
      localStorage.setItem(SEARCH_STRATEGY_KEY, strategy);
    } else {
      localStorage.removeItem(SEARCH_STRATEGY_KEY);
    }
  } catch (error) {
    console.warn("Failed to store search strategy in localStorage:", error);
  }
};

export const getStoredSearchMode = (): SearchMode => {
  try {
    const stored = localStorage.getItem(SEARCH_MODE_KEY);
    if (stored && ['rag', 'ai', 'agent', 'summary'].includes(stored)) {
      return stored as SearchMode;
    }
  } catch (error) {
    console.warn("Failed to read search mode from localStorage:", error);
  }
  return 'agent'; // Default to RAG mode
};

export const setStoredSearchMode = (mode: SearchMode): void => {
  try {
    localStorage.setItem(SEARCH_MODE_KEY, mode);
  } catch (error) {
    console.warn("Failed to store search mode in localStorage:", error);
  }
};
