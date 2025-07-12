import { ArrowBack, CategoryTwoTone } from "@mui/icons-material";
import { Box, Grid, Typography, IconButton } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import SearchDocumentFullCard from "./SearchDocumentFullCard";
import { Document } from "@/models/Search";

interface SimilarSearchResultProps {
  documents: Document[];
  originalDocumentName: string;
  searchType: "all" | "project";
  onBack: () => void;
}

const SimilarSearchResult = ({ 
  documents, 
  originalDocumentName, 
  searchType,
  onBack 
}: SimilarSearchResultProps) => {
  return (
    <Box 
      sx={{ 
        width: "100%",
        "@keyframes slideIn": {
          from: {
            opacity: 0,
            transform: "translateX(100%)",
          },
          to: {
            opacity: 1,
            transform: "translateX(0)",
          },
        },
        animation: "slideIn 0.3s ease-out",
      }}
    >
      {/* Header with back button and title */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
          mb: 3,
          p: 2,
          background: BCDesignTokens.themeBlue10,
          borderRadius: 2,
          border: `2px solid ${BCDesignTokens.themeBlue40}`,
        }}
      >
        <IconButton
          onClick={onBack}
          sx={{
            color: BCDesignTokens.themeBlue80,
            "&:hover": {
              backgroundColor: BCDesignTokens.themeBlue20,
            },
          }}
        >
          <ArrowBack />
        </IconButton>
        <Box>
          <Typography variant="h5" sx={{ color: BCDesignTokens.themeBlue80, fontWeight: 600 }}>
            Similar Documents {searchType === "all" ? "(All Projects)" : "(This Project)"}
          </Typography>
          <Typography variant="body2" sx={{ color: BCDesignTokens.themeGray70 }}>
            Documents similar to: <strong>{originalDocumentName}</strong>
          </Typography>
        </Box>
      </Box>

      {/* Results */}
      {documents.length === 0 ? (
        <Box
          sx={{
            textAlign: "center",
            py: 6,
            color: BCDesignTokens.themeGray60,
          }}
        >
          <Typography variant="h6">No similar documents found</Typography>
        </Box>
      ) : (
        <>
          {/* Group documents by project_id */}
          {Object.entries(
            documents.reduce(
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
                    <SearchDocumentFullCard
                      document={document}
                      showSimilarButtons={false}
                      showProjectName={searchType === "all"}
                    />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))}
        </>
      )}
    </Box>
  );
};

export default SimilarSearchResult;
