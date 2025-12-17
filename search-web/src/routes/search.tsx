import { useEffect, useState } from "react";
import { Cancel, Search as SearchIcon, Settings, Psychology, SmartToy, Summarize, FindInPage } from "@mui/icons-material";
import {
  Box,
  Typography,
  Paper,
  Tooltip,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText
} from "@mui/material";
import { createFileRoute, Navigate } from "@tanstack/react-router";
import { FilterSidebar } from '../components/App/Filters/FilterSideBar';
import { BCDesignTokens } from "epic.theme";
import { useRoles } from "@/contexts/AuthContext";
import { getStoredSearchStrategy, setStoredSearchStrategy, RankingConfig, getStoredRankingConfig, scoreSettings, resultsSettings, getStoredSearchMode, setStoredSearchMode } from "@/utils/searchConfig";
import { SearchMode } from "@/hooks/useSearch";
import { InputBase } from "@mui/material";
import { useSearchQuery, SearchStrategy, SearchRequest } from "@/hooks/useSearch";
import { SearchResponse } from "@/models/Search";
import { LocationControl } from "@/components/Location";
import SearchConfigModal from "@/components/App/Search/SearchConfigModal";
import SearchLanding from "@/components/App/Search/SearchLanding";
import SearchSkelton from "@/components/App/Search/SearchSkelton";
import SearchResult from "@/components/App/Search/SearchResult";
import { ThumbUp, ThumbDown } from "@mui/icons-material";
import FeedbackModal from "@/components/App/Feedback/FeedbackModal";
import { useDocumentTypeMappings } from "@/hooks/useDocumentTypeMappings";
import { useProjects } from "@/hooks/useProjects";
import { PageLoader } from "@/components/PageLoader";

const SIDEBAR_WIDTH = 280;
const COLLAPSED_WIDTH = 56;

export const Route = createFileRoute("/search")({
  component: Search,
  beforeLoad: ({ context }) => {
    const { isAuthenticated, isLoading, signinRedirect } = context.authentication;
    
    // Wait for auth to load before making decision
    if (isLoading) {
      return {};
    }
    
    if (!isAuthenticated) {
      console.log('User not authenticated, redirecting to login');
      signinRedirect();
      return {};
    }
    
    return {};
  },
});

function Search() {
  const { data: rawProjects, isLoading: loadingProjects, isError: projectError } = useProjects();
  const {
    data: rawDocTypes,
    isLoading: loadingDocTypes,
    isError: docTypeError,
  } = useDocumentTypeMappings();

  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem("collapsed");
      return raw ? JSON.parse(raw) : true; // default collapsed
    } catch {
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("collapsed", JSON.stringify(collapsed));
    } catch {}
  }, [collapsed]);

  const [searchText, setSearchText] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [selectedDocTypes, setSelectedDocTypes] = useState<string[]>([]);
  const [searchMode, setSearchMode] = useState<SearchMode>(getStoredSearchMode());
  const [modeMenuAnchor, setModeMenuAnchor] = useState<null | HTMLElement>(null);
  const [feedbackSessionId, setFeedbackSessionId] = useState<string | null>(null);
  const [rankingConfig, setRankingConfig] = useState<RankingConfig>(getStoredRankingConfig());
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<'up' | 'down' | null>(null);

  const { isAdmin, isViewer } = useRoles();

  const handleProjectToggle = (id: string) => {
    setSelectedProjects((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleDocTypeToggle = (id: string) => {
    setSelectedDocTypes((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleClearAll = () => {
    setSelectedProjects([]);
    setSelectedDocTypes([]);
  };

  const handleSaveSearchStrategy = (strategy: SearchStrategy | undefined, newRankingConfig: RankingConfig) => {
    setStoredSearchStrategy(strategy);
    setSearchStrategy(strategy);
    setRankingConfig(newRankingConfig);
  };

  const handleModeChange = (newMode: SearchMode) => {
    setSearchMode(newMode);
    setStoredSearchMode(newMode);
    setModeMenuAnchor(null);
  };

  const handleModeMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setModeMenuAnchor(event.currentTarget);
  };

  const handleModeMenuClose = () => {
    setModeMenuAnchor(null);
  };

  const getModeLabel = (mode: SearchMode): string => {
    switch (mode) {
      case 'rag':
        return 'RAG Search';
      case 'ai':
        return 'AI Search';
      case 'agent':
        return 'Agent Search';
      case 'summary':
        return 'Summary Search';
      default:
        return 'RAG Search';
    }
  };

  const getModeDescription = (mode: SearchMode): string => {
    switch (mode) {
      case 'rag':
        return 'Pure vector search, fastest';
      case 'ai':
        return 'Use NLP to interpret your query and summarize';
      case 'agent':
        return 'Full AI processing with agent capabilities';
      case 'summary':
        return 'Use RAG search and summarize';
      default:
        return 'Pure vector search, fastest';
    }
  };

  const getModeIcon = (mode: SearchMode) => {
    switch (mode) {
      case 'rag':
        return <FindInPage sx={{ fontSize: 24 }} />;
      case 'ai':
        return <Psychology sx={{ fontSize: 24 }} />;
      case 'agent':
        return <SmartToy sx={{ fontSize: 24 }} />;
      case 'summary':
        return <Summarize sx={{ fontSize: 24 }} />;
      default:
        return <SearchIcon sx={{ fontSize: 24 }} />;
    }
  };

  const [searchStrategy, setSearchStrategy] = useState<SearchStrategy | undefined>(() => {
    const stored = getStoredSearchStrategy();

    // Viewer: always default to HYBRID_PARALLEL
    if (isViewer) return "HYBRID_PARALLEL";

    // Admin: use stored value or undefined
    return stored;
  });

  const onSuccess = (data: SearchResponse) => {
    try {
      // Validate the response structure
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid response: Expected object');
      }
      
      if (!data.result) {
        throw new Error('Invalid response: Missing result property');
      }
      
      // Ensure documents array exists or create empty array
      if (!data.result.documents && !data.result.document_chunks) {
        console.warn('Response has no documents or document_chunks, creating empty result');
        data.result.documents = [];
      }
      
      setSearchResults(data);

      // Store feedback session ID if it exists
      if ('feedback_session_id' in data && typeof data.feedback_session_id === 'string') {
        setFeedbackSessionId(data.feedback_session_id);
      } else {
        setFeedbackSessionId(null);
      }
    } catch (error) {
      console.error('Error processing search response:', error);
      // Treat malformed response as an error
      onError(error);
    }
  };

  const onError = (error: any) => {
    console.error('Search error:', error);
    setSearchResults(null);
    
    // You could also show a user-friendly error message here
    // For example, using a toast notification or error state
  };

  const {
    mutate: doSearch,
    isPending,
    error,
    isSuccess,
    reset
  } = useSearchQuery(onSuccess, onError);

  const onSubmitSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    // Prevent double search: don't start new search if one is already in progress
    if (isPending) {
      console.log('Search already in progress, ignoring new search request');
      return;
    }
    
    const searchRequest: SearchRequest = {
      query: searchText,
      searchStrategy: isViewer ? 'HYBRID_PARALLEL' : searchStrategy,
      ...(selectedProjects.length > 0 && { projectIds: selectedProjects }),
      ...(selectedDocTypes.length > 0 && { documentTypeIds: selectedDocTypes }),
      ...(rankingConfig.useCustomRanking && {
        ranking: {
          minScore: scoreSettings[
            isViewer ? "FLEXIBLE" : rankingConfig.scoreSetting
          ],
          topN: resultsSettings[
            isViewer ? "MEDIUM" : rankingConfig.resultsSetting
          ],
        }
      }),
      mode: isViewer ? 'agent' : searchMode,
    };
    doSearch(searchRequest);
  };

  const handleFeedbackClick = (type: 'up' | 'down') => {
    setFeedbackType(type);
    setFeedbackOpen(true);
  };

  useEffect(() => {
    if (!searchText) {
      setSearchResults(null);
      reset();
    }
  }, [searchText]);


  if (loadingProjects || loadingDocTypes) return <PageLoader />;
  if (projectError || docTypeError) return <Navigate to="/error" />;

  return (
    <Box
      sx={{
        display: "flex",
        height: "100%",
        width: "100%",
        paddingTop: "60px",
      }}
    >
      {/* Sidebar */}
      <Box
        sx={{
          width: collapsed ? COLLAPSED_WIDTH : SIDEBAR_WIDTH,
          minWidth: collapsed ? COLLAPSED_WIDTH : SIDEBAR_WIDTH,
          height: "100%",
          minHeight: "calc(100vh - 60px)",
          backgroundColor: "#F1F8FE",
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid rgba(0,0,0,0.12)",
          overflow: "hidden",
        }}
      >
        <FilterSidebar
          rawProjects={rawProjects ?? []}
          rawDocTypes={rawDocTypes}
          selectedProjects={selectedProjects}
          selectedDocTypes={selectedDocTypes}
          onProjectToggle={handleProjectToggle}
          onDocTypeToggle={handleDocTypeToggle}
          onClearAll={handleClearAll}
          collapsed={collapsed}
          onCollapseToggle={() => setCollapsed((s) => !s)}
        />
      </Box>

      {/* Main Content */}
      <Box
        sx={{
          flexGrow: 1,
          p: 3,
          overflow: "auto",
        }}
      >
        <Paper elevation={0} sx={{ p: 3 }}>
          <Typography
            variant="h2"
            sx={{
              mb: 0,
              mt: 2,
              textAlign: "center",
            }}
          >
            Document Search
          </Typography>
          <Typography
            variant="body1"
            sx={{ mb: 4, textAlign: "center" }}
          >
            Search for documents by entering a keyword or phrase below.
          </Typography>
          <Paper
            component="form"
            sx={{
              borderRadius: "16px",
              display: "flex",
              alignItems: "center",
              padding: "8px 16px",
              border: "1px solid",
              borderColor: BCDesignTokens.themeBlue10,
              boxShadow: "0px 2px 6px -2px rgb(0 0 0 / 33%)",
              "&:hover": {
                boxShadow: "0px 2px 18px 0px rgb(85 149 217 / 36%)",
              },
              "&:focus-within": {
                boxShadow: "0px 2px 18px 0px rgb(85 149 217 / 36%)",
              },
            }}
          >
            {isAdmin &&
              <Tooltip title={`${getModeLabel(searchMode)}: ${getModeDescription(searchMode)}`}>
                <IconButton
                  onClick={handleModeMenuOpen}
                  sx={{
                    mr: 1,
                    borderRadius: "12px",
                    minWidth: "48px",
                    height: "48px",
                    color: BCDesignTokens.iconsColorSuccess,
                    backgroundColor: BCDesignTokens.supportSurfaceColorSuccess,
                    "&:hover": {
                      backgroundColor: BCDesignTokens.supportSurfaceColorSuccess,
                    },
                  }}
                >
                  {getModeIcon(searchMode)}
                </IconButton>
              </Tooltip>
            }
            
            <Menu
              anchorEl={modeMenuAnchor}
              open={Boolean(modeMenuAnchor)}
              onClose={handleModeMenuClose}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'left',
              }}
              transformOrigin={{
                vertical: 'top',
                horizontal: 'left',
              }}
              PaperProps={{
                sx: {
                  borderRadius: '12px',
                  boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.1)',
                }
              }}
            >
              <MenuItem 
                onClick={() => handleModeChange('rag')}
                selected={searchMode === 'rag'}
                sx={{
                  px: 2,
                  py: 1.5,
                  backgroundColor: searchMode === 'rag' ? BCDesignTokens.themeBlue10 : 'transparent',
                  '&:hover': {
                    backgroundColor: BCDesignTokens.themeBlue10,
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: '36px' }}>
                  <FindInPage sx={{ fontSize: 20, color: BCDesignTokens.themePrimaryBlue }} />
                </ListItemIcon>
                <ListItemText 
                  primary="RAG Search"
                  secondary="Pure vector search, fastest"
                  secondaryTypographyProps={{
                    sx: { fontSize: '0.75rem', color: BCDesignTokens.themeGray60 }
                  }}
                />
              </MenuItem>
              
              <MenuItem 
                onClick={() => handleModeChange('summary')}
                selected={searchMode === 'summary'}
                sx={{
                  px: 2,
                  py: 1.5,
                  backgroundColor: searchMode === 'summary' ? BCDesignTokens.themeBlue10 : 'transparent',
                  '&:hover': {
                    backgroundColor: BCDesignTokens.themeBlue10,
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: '36px' }}>
                  <Summarize sx={{ fontSize: 20, color: BCDesignTokens.themePrimaryBlue }} />
                </ListItemIcon>
                <ListItemText 
                  primary="Summary Search"
                  secondary="Use RAG search and summarize"
                  secondaryTypographyProps={{
                    sx: { fontSize: '0.75rem', color: BCDesignTokens.themeGray60 }
                  }}
                />
              </MenuItem>
              
              <MenuItem 
                onClick={() => handleModeChange('ai')}
                selected={searchMode === 'ai'}
                sx={{
                  px: 2,
                  py: 1.5,
                  backgroundColor: searchMode === 'ai' ? BCDesignTokens.themeBlue10 : 'transparent',
                  '&:hover': {
                    backgroundColor: BCDesignTokens.themeBlue10,
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: '36px' }}>
                  <Psychology sx={{ fontSize: 20, color: BCDesignTokens.themePrimaryBlue }} />
                </ListItemIcon>
                <ListItemText 
                  primary="AI Search"
                  secondary="Use NLP to interpret your query and summarize"
                  secondaryTypographyProps={{
                    sx: { fontSize: '0.75rem', color: BCDesignTokens.themeGray60 }
                  }}
                />
              </MenuItem>
              
              <MenuItem 
                onClick={() => handleModeChange('agent')}
                selected={searchMode === 'agent'}
                sx={{
                  px: 2,
                  py: 1.5,
                  backgroundColor: searchMode === 'agent' ? BCDesignTokens.themeBlue10 : 'transparent',
                  '&:hover': {
                    backgroundColor: BCDesignTokens.themeBlue10,
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: '36px' }}>
                  <SmartToy sx={{ fontSize: 20, color: BCDesignTokens.themePrimaryBlue }} />
                </ListItemIcon>
                <ListItemText 
                  primary="Agent Search"
                  secondary="Full AI processing with agent capabilities"
                  secondaryTypographyProps={{
                    sx: { fontSize: '0.75rem', color: BCDesignTokens.themeGray60 }
                  }}
                />
              </MenuItem>
            </Menu>
            <InputBase
              sx={{ ml: 1, flex: 1, height: 64 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder={searchMode !== 'rag' ? "Ask AI about documents..." : "Search documents..."}
              inputProps={{ "aria-label": "search text" }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  onSubmitSearch(e);
                }
              }}
            />
            {isAdmin &&
              <Tooltip title="Search Configuration">
                <IconButton
                  type="button"
                  sx={{ p: "10px" }}
                  aria-label="search configuration"
                  size="large"
                  onClick={() => setConfigModalOpen(true)}
                >
                  <Settings sx={{ fontSize: 24, color: BCDesignTokens.themeGray60 }} />
                </IconButton>
              </Tooltip>
            }
            {isPending ? (
              <Tooltip title="Cancel search">
                <IconButton
                  type="button"
                  sx={{ p: "10px" }}
                  aria-label="cancel search"
                  size="large"
                  onClick={() => {
                    reset();
                    setSearchResults(null);
                  }}
                >
                  <Cancel sx={{ fontSize: 30, color: '#d32f2f' }} />
                </IconButton>
              </Tooltip>
            ) : searchText ? (
              <>
                <Tooltip title="Search">
                  <IconButton
                    type="button"
                    sx={{ p: "10px" }}
                    aria-label="search"
                    size="large"
                    onClick={onSubmitSearch}
                  >
                    <SearchIcon sx={{ fontSize: 30 }} />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Clear search">
                  <IconButton
                    type="button"
                    sx={{ p: "10px" }}
                    aria-label="clear search"
                    size="large"
                    onClick={() => setSearchText("")}
                  >
                    <Cancel sx={{ fontSize: 30 }} />
                  </IconButton>
                </Tooltip>
              </>
            ) : (
              <Tooltip title="Search">
                <IconButton
                  type="button"
                  sx={{ p: "10px" }}
                  aria-label="search"
                  size="large"
                  onClick={onSubmitSearch}
                >
                  <SearchIcon sx={{ fontSize: 30 }} />
                </IconButton>
              </Tooltip>
            )}
          </Paper>
          {/* Location Control */}
          {isAdmin &&
            <Box sx={{ mt: 2, mb: 1, display: 'flex', justifyContent: 'center' }}>
              <LocationControl showInSearch />
            </Box>
          }
          {isAdmin &&
            <SearchConfigModal
              open={configModalOpen}
              onClose={() => setConfigModalOpen(false)}
              currentStrategy={searchStrategy}
              onSave={handleSaveSearchStrategy}
            />
          }
          <Box
            sx={{
              mt: 2,
              display: "flex",
              flexDirection: "column",
              alignContent: "center",
              alignItems: "center",
            }}
          >
            {!searchResults && !isPending && !error && <SearchLanding />}
            {isPending && <SearchSkelton />}
            {error && (
              <Box 
                sx={{ 
                  textAlign: 'center', 
                  mt: 4, 
                  p: 3, 
                  borderRadius: 2, 
                  backgroundColor: 'error.light',
                  color: 'error.contrastText'
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Search Error
                </Typography>
                <Typography variant="body1" gutterBottom>
                  {error.message || 'An error occurred while searching. Please try again.'}
                </Typography>
                <Typography variant="body2" sx={{ mt: 2, opacity: 0.8 }}>
                  If the problem persists, please contact support.
                </Typography>
              </Box>
            )}
            {isSuccess && searchResults?.result && (
              <SearchResult 
                searchResults={searchResults} 
                searchText={searchText} 
                searchMode={searchMode}
              />
            )}
          </Box>
          {/* Feedback Modal */}
          {isSuccess && searchResults?.result && (
            <Box
              sx={{
                position: 'fixed',
                bottom: 24,
                right: 24,
                zIndex: 2000,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1.5,
                borderRadius: 2,
                backgroundColor: BCDesignTokens.themeBlue10,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Was this search helpful?
              </Typography>
              <Tooltip title="Yes, this was helpful">
                <IconButton
                  size="small"
                  color="success"
                  onClick={() => handleFeedbackClick('up')}
                >
                  <ThumbUp fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title="No, this was not helpful">
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => handleFeedbackClick('down')}
                >
                  <ThumbDown fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}
          <FeedbackModal
            sessionId={feedbackSessionId ?? undefined}
            open={feedbackOpen}
            onClose={() => setFeedbackOpen(false)}
            initialFeedback={feedbackType}
          />
        </Paper>
      </Box>
    </Box>
  );
}
