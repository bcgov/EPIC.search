import { AutoAwesomeTwoTone, CategoryTwoTone } from "@mui/icons-material";
import { Box, Grid, Typography, CircularProgress } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import SearchDocumentCard from "./SearchDocumentCard";
import SearchDocumentGroupHeader from "./SearchDocumentGroupHeader";
import SimilarSearchResult from "./SimilarSearchResult";
import { SearchResponse, getDocumentsFromResponse, Document } from "@/models/Search";
import { useSimilarSearch } from "@/hooks/useSimilarSearch";
import { useState } from "react";
import { SearchMode } from "@/hooks/useSearch";

interface SearchResultProps {
  searchResults: SearchResponse;
  searchText: string;
  searchMode?: SearchMode;
}

const SearchResult = ({ searchResults, searchText, searchMode }: SearchResultProps) => {
  try {
    // Safety check for searchResults
    if (!searchResults || !searchResults.result) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <Typography variant="h6" color="error">
            No search results available
          </Typography>
        </Box>
      );
    }

    const documents = getDocumentsFromResponse(searchResults);
    const hasDocuments = !!searchResults.result.documents && searchResults.result.documents.length > 0;
    const hasDocumentChunks = !!searchResults.result.document_chunks && searchResults.result.document_chunks.length > 0;
    
    // Separate full documents from chunks for better organization
    const fullDocuments = searchResults.result.documents || [];
    const documentChunks = searchResults.result.document_chunks || [];
  
  // Similar search state
  const [similarResults, setSimilarResults] = useState<{
    documents: Document[];
    originalDocumentName: string;
    searchType: "all" | "project";
  } | null>(null);
  
  const similarSearchMutation = useSimilarSearch();

  const handleSimilarSearch = async (documentId: string, projectIds?: string[]) => {
    const originalDocument = documents.find(doc => doc.document_id === documentId);
    if (!originalDocument) return;

    try {
      const result = await similarSearchMutation.mutateAsync({
        documentId,
        projectIds,
        limit: 5
      });

      setSimilarResults({
        documents: result.result.documents,
        originalDocumentName: originalDocument.document_name,
        searchType: projectIds ? "project" : "all",
      });
    } catch (error) {
      console.error("Error fetching similar documents:", error);
    }
  };

  const handleBackToOriginal = () => {
    setSimilarResults(null);
  };

  // Show similar results if available
  if (similarResults) {
    return (
      <SimilarSearchResult
        documents={similarResults.documents}
        originalDocumentName={similarResults.originalDocumentName}
        searchType={similarResults.searchType}
        onBack={handleBackToOriginal}
      />
    );
  }

  // Show loading state for similar search
  if (similarSearchMutation.isPending) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          py: 6,
        }}
      >
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Finding similar documents...</Typography>
      </Box>
    );
  }

  return (
    <>
      {/* AI Summary Section */}
      <Box
        sx={{
          mb: 6,
          border: '1px solid',
          borderColor: BCDesignTokens.themeBlue50,
          backgroundColor: BCDesignTokens.themeBlue10,
          borderRadius: "8px",
          p: 2,
        }}
      >
        <Box display="flex" alignItems="flex-start" gap={2}>
          {/* Icon on the left */}
          <Box mt={0.5} flexShrink={0}>
            {searchMode === 'rag' ? (
              <CategoryTwoTone sx={{ fontSize: 20, color: 'primary.main' }} />
            ) : (
              <AutoAwesomeTwoTone sx={{ fontSize: 30, color: BCDesignTokens.themeBlue80 }} />
            )}
          </Box>

          {/* Main content */}
          <Box flex={1}>
              <Typography
                component="p"
                sx={{
                  color: '#374151', // Tailwind's text-gray-700
                  fontSize: '0.875rem', // text-sm
                  lineHeight: 1.625, // leading-relaxed
                }}
              >
              {searchResults.result.response}
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* Render Document Chunks if they exist */}
      {hasDocumentChunks && (
        <Box sx={{ width: "100%" }}>
          {/* Group document chunks by project_id, then by document_id */}
          {Object.entries(
            documentChunks.reduce(
              (projectGroups: Record<string, { 
                projectName: string; 
                documentGroups: Record<string, { 
                  document: Document; 
                  chunks: Document[] 
                }> 
              }>, document) => {
                const projectId = document.project_id;
                const documentId = document.document_id;
                
                if (!projectGroups[projectId]) {
                  projectGroups[projectId] = {
                    projectName: document.project_name,
                    documentGroups: {},
                  };
                }
                
                if (!projectGroups[projectId].documentGroups[documentId]) {
                  projectGroups[projectId].documentGroups[documentId] = {
                    document: document,
                    chunks: [],
                  };
                }
                
                projectGroups[projectId].documentGroups[documentId].chunks.push(document);
                return projectGroups;
              },
              {}
            )
          ).map(([projectId, projectGroup], projectIndex) => (
            <Box
              key={`chunks-${projectIndex}`}
              sx={{
                width: "100%",
                mb: 3,
                pb: 2,
                borderBottom: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
              }}
            >
              <Typography
                variant="h3"
                sx={{
                  pb: 1,
                  color: BCDesignTokens.themeBlue100,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                }}
                aria-label={`Project ${projectId}`}
              >
                {projectGroup.projectName}
              </Typography>
              
              {/* Document groups within this project */}
              {Object.entries(projectGroup.documentGroups).map(([, documentGroup], documentIndex) => (
                <Box key={`chunk-doc-${documentIndex}`} sx={{ mb: 3 }}>
                  {/* Document header */}
                  <SearchDocumentGroupHeader 
                    document={documentGroup.document} 
                    onSimilarSearch={handleSimilarSearch}
                  />
                  
                  {/* Chunks for this document */}
                  <Grid container spacing={2} alignItems="stretch">
                    {documentGroup.chunks.map((chunk, chunkIndex) => (
                      <Grid
                        item
                        xs={12}
                        md={6}
                        lg={4}
                        key={`chunk-${chunkIndex}`}
                        sx={{ display: "flex", marginLeft: '50px' }}
                      >
                        <SearchDocumentCard
                          document={chunk}
                          searchText={searchText}
                          isChunk={true}
                          showSimilarButtons={false}
                        />
                      </Grid>
                    ))}
                  </Grid>
                </Box>
              ))}
            </Box>
          ))}
        </Box>
      )}

      {/* Divider between sections if both exist */}
      {hasDocumentChunks && hasDocuments && (
        <Box sx={{ 
          width: "100%", 
          height: "2px", 
          backgroundColor: BCDesignTokens.themeBlue80, 
          my: 4,
          borderRadius: "1px"
        }} />
      )}

      {/* Render Full Documents if they exist */}
      {hasDocuments && (
        <Box sx={{ width: "100%" }}>
          {/* Group full documents by project */}
          {Object.entries(
            fullDocuments.reduce(
              (groups: Record<string, { projectName: string; documents: Document[] }>, document) => {
                const projectId = document.project_id;
                if (!groups[projectId]) {
                  groups[projectId] = {
                    projectName: document.project_name,
                    documents: [],
                  };
                }
                groups[projectId].documents.push(document);
                return groups;
              },
              {}
            )
          ).map(([projectId, group], index) => (
            <Box
              key={`docs-${index}`}
              sx={{
                width: "100%",
                mb: 3,
                pb: 2,
                borderBottom: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
              }}
            >
              <Typography
                variant="h4"
                sx={{
                  pb: 1,
                  color: BCDesignTokens.themeBlue80,
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                }}
                aria-label={`Project ${projectId}`}
              >
                <CategoryTwoTone />
                {group.projectName}
              </Typography>
              <Grid container spacing={2} alignItems="stretch">
                {group.documents.map((document, docIndex) => (
                  <Grid
                    item
                    xs={12}
                    md={6}
                    lg={4}
                    key={`doc-${docIndex}`}
                    sx={{ display: "flex" }}
                  >
                    <SearchDocumentCard
                      document={document}
                      searchText={searchText}
                      isChunk={false}
                      onSimilarSearch={handleSimilarSearch}
                      showSimilarButtons={true}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))}
        </Box>
      )}
    </>
  );
} catch (error) {
  console.error('Error rendering search results:', error);
  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
      <Typography variant="h6" color="error">
        Error displaying search results. Please try again.
      </Typography>
    </Box>
  );
}
};

export default SearchResult;
