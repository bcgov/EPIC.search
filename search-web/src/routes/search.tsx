import { Cancel, Search as SearchIcon, Settings, FilterList } from "@mui/icons-material";
import { Box, Container, Typography, Tooltip, IconButton, Chip, Alert } from "@mui/material";
import { InputBase } from "@mui/material";
import { Paper } from "@mui/material";
import { createFileRoute } from "@tanstack/react-router";
import { BCDesignTokens } from "epic.theme";
import { useEffect, useState } from "react";
import { useSearchQuery, SearchStrategy, SearchRequest } from "@/hooks/useSearch";
import { SearchResponse } from "@/models/Search";
import SearchSkelton from "@/components/App/Search/SearchSkelton";
import SearchResult from "@/components/App/Search/SearchResult";
import SearchLanding from "@/components/App/Search/SearchLanding";
import SearchConfigModal from "@/components/App/Search/SearchConfigModal";
import FilterModal from "@/components/App/Search/FilterModal";
import { useDocumentTypeMappings } from "@/hooks/useDocumentTypeMappings";
import { getStoredSearchStrategy, setStoredSearchStrategy, RankingConfig, getStoredRankingConfig, scoreSettings, resultsSettings } from "@/utils/searchConfig";
import { useProjects } from "@/hooks/useProjects";
import ProjectLoadingScreen from "@/components/App/Search/ProjectLoadingScreen";
import { AppConfig } from "@/utils/config";

export const Route = createFileRoute("/search")({
  component: Search,
});

function Search() {
  const [searchText, setSearchText] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [searchStrategy, setSearchStrategy] = useState<SearchStrategy | undefined>(getStoredSearchStrategy());
  const [rankingConfig, setRankingConfig] = useState<RankingConfig>(getStoredRankingConfig());
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
  const [selectedDocumentTypeIds, setSelectedDocumentTypeIds] = useState<string[]>([]);

  const { isLoading: projectsLoading, isError: projectsError, data: allProjects } = useProjects();
  const { data: allDocTypes } = useDocumentTypeMappings();

  const onSuccess = (data: SearchResponse) => {
    setSearchResults(data);
  };

  const onError = (error: any) => {
    console.error(error);
  };

  useEffect(() => {
    if (!searchText) {
      setSearchResults(null);
      reset();
    }
  }, [searchText]);

  const {
    mutate: doSearch,
    isPending,
    error,
    isSuccess,
    reset
  } = useSearchQuery(onSuccess, onError);

  const onSubmitSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const searchRequest: SearchRequest = {
      question: searchText,
      ...(searchStrategy && { searchStrategy }),
      ...(selectedProjectIds.length > 0 && { projectIds: selectedProjectIds }),
      ...(selectedDocumentTypeIds.length > 0 && { documentTypeIds: selectedDocumentTypeIds }),
      ...(rankingConfig.useCustomRanking && {
        ranking: {
          minScore: scoreSettings[rankingConfig.scoreSetting],
          topN: resultsSettings[rankingConfig.resultsSetting]
        }
      })
    };
    doSearch(searchRequest);
  };

  const handleSaveSearchStrategy = (strategy: SearchStrategy | undefined, newRankingConfig: RankingConfig) => {
    setStoredSearchStrategy(strategy);
    setSearchStrategy(strategy);
    setRankingConfig(newRankingConfig);
  };

  if (projectsLoading) {
    return <ProjectLoadingScreen />;
  }
  if (projectsError) {
    return <Box sx={{ p: 6, textAlign: "center" }}>
      <Typography color="error" variant="h5">Failed to load project list. Please try again later.</Typography>
    </Box>;
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 1 }}>
      {AppConfig.systemNote && (
        <Alert 
          severity="info" 
          sx={{ 
            mb: 3, 
            mt: 2,
            borderRadius: "8px",
            textAlign: "center"
          }}
        >
          {AppConfig.systemNote}
        </Alert>
      )}
      <Typography
        variant="h2"
        sx={{
          mb: 0,
          mt: 2,
          textAlign: "center",
          color: BCDesignTokens.themePrimaryBlue,
        }}
      >
        Document Search
      </Typography>
      <Typography
        variant="body1"
        sx={{ mb: 4, textAlign: "center", color: BCDesignTokens.themeBlue90 }}
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
        <InputBase
          sx={{ ml: 1, flex: 1, height: 64 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search text..."
          inputProps={{ "aria-label": "search text" }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onSubmitSearch(e);
            }
          }}
        />
        <Tooltip title="Filter by Project">
          <IconButton
            type="button"
            sx={{ p: "10px" }}
            aria-label="filter projects"
            size="large"
            onClick={() => setFilterModalOpen(true)}
          >
            <FilterList sx={{ fontSize: 24, color: BCDesignTokens.themeGray60 }} />
          </IconButton>
        </Tooltip>
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
        {searchText && (
          <IconButton
            type="button"
            sx={{ p: "10px" }}
            aria-label="clear search"
            size="large"
            onClick={() => setSearchText("")}
          >
            <Cancel sx={{ fontSize: 30 }} />
          </IconButton>
        )}
        {!searchText && (
          <IconButton
            type="button"
            sx={{ p: "10px" }}
            aria-label="search"
            size="large"
            onClick={onSubmitSearch}
          >
            <SearchIcon sx={{ fontSize: 30 }} />
          </IconButton>
        )}
      </Paper>

      {/* Show selected project and document type chips below the search bar */}
      {(selectedProjectIds.length > 0 || selectedDocumentTypeIds.length > 0) && (
        <Box sx={{ mt: 1, mb: 1, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {selectedProjectIds.length > 0 && allProjects && selectedProjectIds.map((id) => {
            const proj = allProjects.find((p) => p.project_id === id);
            return proj ? (
              <Chip
                key={id}
                label={proj.project_name}
                color="primary"
                sx={{ color: '#fff', fontWeight: 600, borderRadius: 3 }}
                onDelete={() => {
                  setSelectedProjectIds((prev) => prev.filter((pid) => pid !== id));
                }}
              />
            ) : null;
          })}
          {selectedDocumentTypeIds.length > 0 && allDocTypes &&
            Object.entries(allDocTypes.result.document_type_mappings).flatMap(([, types]) =>
              Object.entries(types).map(([typeId, typeName]) =>
                selectedDocumentTypeIds.includes(typeId) ? (
                  <Chip
                    key={typeId}
                    label={typeName}
                    color="secondary"
                    sx={{ color: '#fff', fontWeight: 600, borderRadius: 3 }}
                    onDelete={() => {
                      setSelectedDocumentTypeIds((prev) => prev.filter((tid) => tid !== typeId));
                    }}
                  />
                ) : null
              )
            )}
        </Box>
      )}

      <SearchConfigModal
        open={configModalOpen}
        onClose={() => setConfigModalOpen(false)}
        currentStrategy={searchStrategy}
        onSave={handleSaveSearchStrategy}
      />
      <FilterModal
        open={filterModalOpen}
        onClose={() => setFilterModalOpen(false)}
        selectedProjectIds={selectedProjectIds}
        selectedDocumentTypeIds={selectedDocumentTypeIds}
        onSave={(projIds, docTypeIds) => {
          setSelectedProjectIds(projIds);
          setSelectedDocumentTypeIds(docTypeIds);
        }}
      />

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
        {error && <Typography>Error: {error.message}</Typography>}
        {isSuccess && searchResults?.result && (
          <SearchResult 
            searchResults={searchResults} 
            searchText={searchText} 
            searchStrategy={searchStrategy}
          />
        )}
      </Box>
    </Container>
  );
}
