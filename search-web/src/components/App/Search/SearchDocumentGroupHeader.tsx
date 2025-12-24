import { Box, Typography, Tooltip, IconButton } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { DescriptionTwoTone, FindInPage, Business, OpenInNew } from "@mui/icons-material";
import FileLink from "@/components/Shared/FileLink";
import DocumentTypeChip, { getDocumentTypeIconColor } from "@/components/Shared/DocumentTypeChip";

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
        background: BCDesignTokens.themeBlue10,
        padding: 2,
        borderRadius: 2,
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
        position: "relative",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 2,
        }}
      >
        <DescriptionTwoTone
          className="document-icon"
          sx={{ 
            fontSize: 25,
            color: getDocumentTypeIconColor(document.document_type),
            mb: "40px",
          }}
        />
        <Box sx={{ flex: 1 }}>
          <Typography
            className="document-title"
            variant="body1"
            sx={{
              fontWeight: 400,
              lineHeight: 1.2,
              transition: "color 0.2s ease",
            }}
          >
            {document.document_display_name}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: BCDesignTokens.themeGray70,
              fontWeight: 400,
              fontSize: "0.85rem",
              mt: 0.25,
            }}
          >
            {document.document_name}
          </Typography>
          {document.document_type && (
            <Box sx={{ mt: 0.5 }}>
              <DocumentTypeChip documentType={document.document_type} />
            </Box>
          )}
        </Box>
      </Box>

      <Box sx={{ position: "absolute", top: 12, right: 12, display: "flex", alignItems: "center" }}>
        {document.s3_key && (
          <FileLink
            s3Key={document.s3_key}
            fileName={document.document_saved_name}
            projectId={document.project_id}
            documentName={document.document_name}
          >
            <Tooltip title="Open document in a new tab">
              <IconButton
                size="small"
                sx={{
                  backgroundColor: BCDesignTokens.themeBlue10,
                  "&:hover": { backgroundColor: BCDesignTokens.themeGray40 },
                }}
              >
                <OpenInNew sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </FileLink>
        )}
        {onSimilarSearch && (
          <>
            <Tooltip title="Find similar documents in this project only">
              <IconButton
                size="small"
                sx={{
                  backgroundColor: BCDesignTokens.themeBlue10,
                  "&:hover": { backgroundColor: BCDesignTokens.themeGray40 },
                  color: 'secondary.main',
                }}
                onClick={handleSimilarThisProject}
              >
                <Business sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
            <Tooltip title="Find similar documents across all projects">
              <IconButton
                size="small"
                sx={{
                  backgroundColor: BCDesignTokens.themeBlue10,
                  "&:hover": { backgroundColor: BCDesignTokens.themeGray40 },
                  color: 'primary.main',
                }}
                onClick={handleSimilarAllProjects}
              >
                <FindInPage sx={{ fontSize: 16 }} />
              </IconButton>
            </Tooltip>
          </>
        )}
      </Box>
    </Box>
  );
};

export default SearchDocumentGroupHeader;
