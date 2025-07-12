import { Box, Typography, Button, Tooltip } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { DescriptionTwoTone, FindInPage, Business } from "@mui/icons-material";
import PdfLink from "@/components/Shared/PdfLink";

interface SearchDocumentFullCardProps {
  document: Document;
  onSimilarSearch?: (documentId: string, projectIds?: string[]) => void;
  showSimilarButtons?: boolean;
  showProjectName?: boolean;
}

const SearchDocumentFullCard = ({ 
  document, 
  onSimilarSearch,
  showSimilarButtons = true,
  showProjectName = false 
}: SearchDocumentFullCardProps) => {
  const handleSimilarAllProjects = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSimilarSearch?.(document.document_id);
  };

  const handleSimilarThisProject = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onSimilarSearch?.(document.document_id, [document.project_id]);
  };
  return (
    <Box
      sx={{
        my: 1,
        background: BCDesignTokens.themeBlue10,
        padding: 2,
        borderRadius: 2,
        height: 260,
        display: "flex",
        flexDirection: "column",
        whiteSpace: "normal",
        overflow: "auto",
        position: "relative",
      }}
    >
      <PdfLink
        s3Key={document.s3_key || null}
        fileName={document.document_saved_name}
        pageNumber={parseInt(document.page_number || "1", 10)}
        projectId={document.project_id}
        documentName={document.document_name}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            height: "100%",
            cursor: "pointer",
            "&:hover": {
              "& .document-icon": {
                color: BCDesignTokens.themeBlue80,
              },
            },
          }}
        >
          <DescriptionTwoTone
            className="document-icon"
            color="primary"
            sx={{ 
              fontSize: 80,
              transition: "color 0.2s ease",
            }}
          />
          <Typography
            variant="h6"
            sx={{
              textAlign: "center",
              color: BCDesignTokens.themeGray80,
              fontWeight: 500,
              px: 1,
            }}
          >
            {document.document_name}
          </Typography>
          {showProjectName && (
            <Typography
              variant="caption"
              sx={{
                textAlign: "center",
                color: BCDesignTokens.themeBlue70,
                fontWeight: 600,
                px: 1,
                mt: 0.5,
                backgroundColor: BCDesignTokens.themeBlue20,
                borderRadius: 1,
                padding: "2px 8px",
                fontSize: "0.75rem",
              }}
            >
              {document.project_name}
            </Typography>
          )}
        </Box>
      </PdfLink>
      
      {showSimilarButtons && onSimilarSearch && (
        <Box
          sx={{
            position: "absolute",
            bottom: 8,
            left: 8,
            right: 8,
            display: "flex",
            gap: 1,
            flexDirection: "column",
          }}
        >
          <Tooltip title="Find similar documents in this project only">
            <Button
              size="small"
              variant="outlined"
              color="secondary"
              onClick={handleSimilarThisProject}
              startIcon={<Business />}
              sx={{
                fontSize: "0.7rem",
                padding: "4px 8px",
                backgroundColor: "rgba(255, 255, 255, 0.9)",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 1)",
                },
              }}
            >
              Similar (Project)
            </Button>
          </Tooltip>
          <Tooltip title="Find similar documents across all projects">
            <Button
              size="small"
              variant="outlined"
              color="primary"
              onClick={handleSimilarAllProjects}
              startIcon={<FindInPage />}
              sx={{
                fontSize: "0.7rem",
                padding: "4px 8px",
                backgroundColor: "rgba(255, 255, 255, 0.9)",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 1)",
                },
              }}
            >
              Similar (All)
            </Button>
          </Tooltip>
        </Box>
      )}
    </Box>
  );
};

export default SearchDocumentFullCard;
