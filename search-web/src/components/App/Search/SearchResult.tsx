import { AutoAwesomeTwoTone, CategoryTwoTone } from "@mui/icons-material";
import { Box, Grid, Typography, CircularProgress } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import SearchDocumentCard from "./SearchDocumentCard";
import SimilarSearchResult from "./SimilarSearchResult";
import { SearchResponse, getDocumentsFromResponse, Document } from "@/models/Search";
import { useSimilarSearch } from "@/hooks/useSimilarSearch";
import { useState } from "react";

interface SearchResultProps {
  searchResults: SearchResponse;
  searchText: string;
}

const SearchResult = ({ searchResults, searchText }: SearchResultProps) => {
  const documents = getDocumentsFromResponse(searchResults);
  const hasDocumentChunks = !!searchResults.result.document_chunks;
  
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
        limit: 5,
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
          width: "calc(100% - 32px)",
          mt: 1,
          mb: 3,
          background: BCDesignTokens.themeBlue10,
          padding: 2,
          borderRadius: "16px",
          position: "relative",
          overflow: "hidden",
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            borderRadius: "16px",
            padding: "3px",
            background: `linear-gradient(45deg, ${BCDesignTokens.themeBlue60}, ${BCDesignTokens.themeGold50})`,
            WebkitMask:
              "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
            WebkitMaskComposite: "xor",
            maskComposite: "exclude",
            pointerEvents: "none",
          },
          boxShadow: "0 0 4px rgba(62, 216, 255, 0.5)",
          animation: "glowing 2s ease-in-out infinite alternate",
          "@keyframes glowing": {
            "0%": {
              boxShadow: "0 0 4px rgba(63, 212, 249, 0.66)",
            },
            "100%": {
              boxShadow: "0 0 8px rgba(233, 239, 45, 0.8)",
            },
          },
        }}
      >
        <Typography variant="body1">
          {searchResults.result.response}
        </Typography>
        <Typography
          variant="caption"
          sx={{
            fontWeight: "bold",
            display: "flex",
            alignItems: "center",
            justifyContent: "flex-end",
            gap: 1,
          }}
        >
          <AutoAwesomeTwoTone color="primary" /> 
          {hasDocumentChunks ? "Semantic Search Results" : "Document Search Results"}
        </Typography>
      </Box>

      {/* Group documents by project_id */}
      {Object.entries(
        documents.reduce(
          (groups: Record<string, { projectName: string; documents: typeof documents }>, document) => {
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
          key={index}
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
                key={docIndex}
                sx={{ display: "flex" }}
              >
                <SearchDocumentCard
                  document={document}
                  searchText={searchText}
                  isChunk={hasDocumentChunks}
                  onSimilarSearch={handleSimilarSearch}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      ))}
    </>
  );
};

export default SearchResult;
