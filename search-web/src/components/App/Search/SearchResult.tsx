import { AutoAwesomeTwoTone, CategoryTwoTone } from "@mui/icons-material";
import { Box, Grid, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import SearchDocumentCard from "./SearchDocumentCard";
import { SearchResponse } from "@/models/Search";

interface SearchResultProps {
  searchResults: SearchResponse;
  searchText: string;
}

const SearchResult = ({ searchResults, searchText }: SearchResultProps) => {
  return (
    <>
      <Box
        sx={{
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
        <Typography variant="body1">{searchResults.result.response}</Typography>
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
          <AutoAwesomeTwoTone color="primary" /> Summarized by AI
        </Typography>
      </Box>

      {/* Group documents by project_id */}
      {Object.entries(
        searchResults?.result.documents.reduce(
          (groups, document) => {
            const projectId = document.project_id;
            if (!groups[projectId]) {
              groups[projectId] = {
                projectName: document.project_name,
                documents: [],
              };
            }
            groups[projectId].documents.push(document);
            console.log("groups", groups);
            return groups;
          },
          {} as Record<
            string,
            {
              projectName: string;
              documents: typeof searchResults.result.documents;
            }
          >
        )
      ).map(([projectId, group]) => (
        <Box
          key={projectId}
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
          >
            <CategoryTwoTone />
            {group.projectName}
          </Typography>
          <Grid container spacing={2} alignItems="stretch">
            {group.documents.map((document) => (
              <Grid
                item
                xs={12}
                md={6}
                lg={4}
                key={document.document_id}
                sx={{ display: "flex" }}
              >
                <SearchDocumentCard
                  document={document}
                  searchText={searchText}
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
