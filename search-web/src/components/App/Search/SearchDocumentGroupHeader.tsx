import { Box, Typography, Button, Tooltip } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { DescriptionTwoTone, FindInPage, Business } from "@mui/icons-material";
import PdfLink from "@/components/Shared/PdfLink";

interface SearchDocumentGroupHeaderProps {
  document: Document;
  onSimilarSearch?: (documentId: string, projectIds?: string[]) => void;
}

const SearchDocumentGroupHeader = ({ document, onSimilarSearch }: SearchDocumentGroupHeaderProps) => {
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
        mb: 2,
        background: BCDesignTokens.themeGray10,
        padding: 2,
        borderRadius: 2,
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
        position: "relative",
      }}
    >
      <PdfLink
        s3Key={document.s3_key || null}
        fileName={document.document_saved_name}
        projectId={document.project_id}
        documentName={document.document_name}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            cursor: "pointer",
            "&:hover": {
              "& .document-icon": {
                color: BCDesignTokens.themeBlue80,
              },
              "& .document-title": {
                color: BCDesignTokens.themeBlue80,
              },
            },
          }}
        >
          <DescriptionTwoTone
            className="document-icon"
            color="primary"
            sx={{ 
              fontSize: 32,
              transition: "color 0.2s ease",
            }}
          />
          <Box sx={{ flex: 1 }}>
            <Typography
              className="document-title"
              variant="h6"
              sx={{
                color: BCDesignTokens.themeGray80,
                fontWeight: 600,
                lineHeight: 1.2,
                transition: "color 0.2s ease",
              }}
            >
              {document.document_display_name}
            </Typography>
            <Typography
              variant="body2"
              sx={{
                color: BCDesignTokens.themeGray60,
                fontWeight: 400,
                fontSize: "0.85rem",
                fontStyle: "italic",
                mt: 0.25,
              }}
            >
              {document.document_name}
            </Typography>
            {document.document_type && (
              <Typography
                variant="caption"
                sx={{
                  color: BCDesignTokens.themeGray70,
                  fontWeight: 500,
                  fontSize: "0.75rem",
                  mt: 0.25,
                  backgroundColor: BCDesignTokens.themeGray20,
                  borderRadius: 1,
                  padding: "1px 6px",
                  display: "inline-block",
                }}
              >
                {document.document_type}
              </Typography>
            )}
          </Box>
        </Box>
      </PdfLink>
      
      {onSimilarSearch && (
        <Box
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            display: "flex",
            gap: 0.5,
            flexDirection: "row",
          }}
        >
          <Tooltip title="Find similar documents in this project only">
            <Button
              size="small"
              variant="outlined"
              color="secondary"
              onClick={handleSimilarThisProject}
              sx={{
                fontSize: "0.6rem",
                padding: "4px",
                minWidth: "auto",
                backgroundColor: "rgba(255, 255, 255, 0.95)",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 1)",
                },
              }}
            >
              <Business sx={{ fontSize: 16 }} />
            </Button>
          </Tooltip>
          <Tooltip title="Find similar documents across all projects">
            <Button
              size="small"
              variant="outlined"
              color="primary"
              onClick={handleSimilarAllProjects}
              sx={{
                fontSize: "0.6rem",
                padding: "4px",
                minWidth: "auto",
                backgroundColor: "rgba(255, 255, 255, 0.95)",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 1)",
                },
              }}
            >
              <FindInPage sx={{ fontSize: 16 }} />
            </Button>
          </Tooltip>
        </Box>
      )}
    </Box>
  );
};

export default SearchDocumentGroupHeader;
