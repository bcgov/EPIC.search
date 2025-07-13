import { Box, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { DescriptionTwoTone } from "@mui/icons-material";
import PdfLink from "@/components/Shared/PdfLink";

interface SearchDocumentGroupHeaderProps {
  document: Document;
}

const SearchDocumentGroupHeader = ({ document }: SearchDocumentGroupHeaderProps) => {
  return (
    <Box
      sx={{
        mb: 2,
        background: BCDesignTokens.themeGray10,
        padding: 2,
        borderRadius: 2,
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
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
          </Box>
        </Box>
      </PdfLink>
    </Box>
  );
};

export default SearchDocumentGroupHeader;
