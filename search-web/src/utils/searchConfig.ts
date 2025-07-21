import { SearchStrategy } from "@/hooks/useSearch";

const SEARCH_STRATEGY_KEY = "epic-search-strategy";

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

export const searchStrategyOptions = [
  {
    value: undefined,
    label: "Default",
    description: "Use the default search strategy (HYBRID_SEMANTIC_FALLBACK)"
  },
  {
    value: "HYBRID_SEMANTIC_FALLBACK" as SearchStrategy,
    label: "Hybrid Semantic Fallback",
    description: "Document keyword filter → Semantic search → Keyword fallback. Optimal balance of efficiency and accuracy for most queries."
  },
  {
    value: "HYBRID_KEYWORD_FALLBACK" as SearchStrategy,
    label: "Hybrid Keyword Fallback",
    description: "Document keyword filter → Keyword search → Semantic fallback. Better for queries with specific terms or technical vocabulary."
  },
  {
    value: "SEMANTIC_ONLY" as SearchStrategy,
    label: "Semantic Only",
    description: "Pure semantic search without keyword filtering or fallbacks. Best for conceptual queries where exact keyword matches aren't important."
  },
  {
    value: "KEYWORD_ONLY" as SearchStrategy,
    label: "Keyword Only",
    description: "Pure keyword search without semantic components. Fastest option, best for exact term matching."
  },
  {
    value: "HYBRID_PARALLEL" as SearchStrategy,
    label: "Hybrid Parallel",
    description: "Run semantic and keyword searches simultaneously and merge results. Comprehensive coverage but higher computational cost."
  },
  {
    value: "DOCUMENT_ONLY" as SearchStrategy,
    label: "Document Only",
    description: "Direct document-level search without chunk analysis. Fastest option for document browsing and type-based filtering."
  }
];
