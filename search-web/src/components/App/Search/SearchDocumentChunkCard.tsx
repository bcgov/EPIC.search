import { Box, Button, Chip, Typography, IconButton, Tooltip } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { useState, useRef, useEffect } from "react";
import { DescriptionTwoTone, OpenInNew } from "@mui/icons-material";
import FileLink from "@/components/Shared/FileLink";

interface SearchDocumentChunkCardProps {
  document: Document;
  searchText: string;
}

const SearchDocumentChunkCard = ({
  document,
  searchText,
}: SearchDocumentChunkCardProps) => {
  const [expanded, setExpanded] = useState(false);
  const [contentOverflows, setContentOverflows] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Check if content height exceeds 150px
    if (contentRef.current) {
      const isOverflowing = contentRef.current.scrollHeight > 150;
      setContentOverflows(isOverflowing);
    }
  }, [document.content]);

  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  // Function to highlight search text in content
  const highlightSearchText = (text: string, searchTerm: string) => {
    // Safety checks
    if (!text || typeof text !== 'string') {
      return text || '';
    }
    
    if (!searchTerm || typeof searchTerm !== 'string' || !searchTerm.trim()) {
      return text;
    }

    try {
      const parts = text.split(new RegExp(`(${searchTerm})`, "gi"));

      return parts.map((part, index) =>
        part.toLowerCase() === searchTerm.toLowerCase() ? (
          <span
            key={index}
            style={{ backgroundColor: BCDesignTokens.themeGold40 }}
          >
            {part}
          </span>
        ) : (
          part
        )
      );
    } catch (error) {
      console.warn('Error highlighting text:', error);
      return text;
    }
  };

  return (
    <Box
      sx={{
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
        padding: 2,
        borderRadius: 2,
        height: expanded ? "auto" : 180,
        display: "flex",
        flexDirection: "column",
        whiteSpace: "normal",
        overflow: "auto",
        position: "relative",
      }}
    >
      {/* Open Document Icon */}
      <Tooltip title="Open document at this page">
        <IconButton
          sx={{
            position: "absolute",
            top: 8,
            right: 8,
            "&:hover": { backgroundColor: BCDesignTokens.themeGray40 },
            width: 32,
            height: 32,
            padding: 3,
          }}
        >          
          <FileLink
            s3Key={document.s3_key || null}
            fileName={document.document_saved_name}
            pageNumber={parseInt(document.page_number || "1", 10)}
            projectId={document.project_id}
            documentName={document.document_name}
          >
            <OpenInNew sx={{ fontSize: 16 }} />
          </FileLink>
        </IconButton>
      </Tooltip>

      <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
        <Chip
          size="small"
          variant="outlined"
          label={`Page ${document.page_number}`}
          icon={<DescriptionTwoTone sx={{ fontSize: 20, color: BCDesignTokens.themeBlue80 }} />}
          sx={{
            my: 0.75,
            borderRadius: 1.5,
            display: "flex",
            alignItems: "center",
            backgroundColor: BCDesignTokens.themeGray20,
            border: `1px solid #FFF`,
            padding: 1,
          }}
        />
      </Box>
      <Box
        sx={{
          position: "relative",
          flex: 1,
        }}
      >
        <Typography
          ref={contentRef}
          variant="body2"
          color={BCDesignTokens.themeGray80}
          sx={{
            display: "-webkit-box",
            WebkitLineClamp: expanded ? "none" : 5,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {highlightSearchText(document.content, searchText)}
        </Typography>
      </Box>
        {contentOverflows && (
          <Box sx={{ display: "flex", justifyContent: "left" }}>
            <Typography
              component="a"
              onClick={toggleExpand}
              sx={{
                cursor: "pointer",
                color: BCDesignTokens.themeBlue100,
                fontSize: "0.875rem",
                "&:hover": {
                  color: BCDesignTokens.themeBlue80,
                },
                paddingTop: 1,
              }}
            >
              {expanded ? "Read Less" : "Read More"}
            </Typography>
          </Box>
        )}
    </Box>
  );
};

export default SearchDocumentChunkCard;
