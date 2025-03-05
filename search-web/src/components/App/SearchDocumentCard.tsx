import { Box, Button, Chip, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { useState, useRef, useEffect } from "react";

interface SearchDocumentCardProps {
  document: Document;
}

const SearchDocumentCard = ({ document }: SearchDocumentCardProps) => {
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

  return (
    <Box
      sx={{
        my: 1,
        background: BCDesignTokens.themeBlue10,
        padding: 2,
        borderRadius: 2,
      }}
    >
      <Typography
        variant="h5"
        fontWeight="normal"
        color={BCDesignTokens.themePrimaryBlue}
      >
        {document.project_name}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: "bold"}}>
        {document.document_saved_name}
      </Typography>
      <Chip
        size="small"
        label={`Page ${document.page_number}`}
        sx={{
          fontWeight: "normal",
          my: 0.75,
          borderRadius: 1.5,
        }}
      />
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          height: expanded ? "auto" : "150px",
          transition: "height 0.3s ease",
        }}
      >
        <Typography
          ref={contentRef}
          variant="body2"
          color={BCDesignTokens.themeGray80}
        >
          " {document.content} "
        </Typography>
        {!expanded && contentOverflows && (
          <Box
            sx={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              height: "50px",
              background:
                "linear-gradient(transparent, rgba(230, 242, 255, 0.9))",
            }}
          />
        )}
      </Box>
      {contentOverflows && (
        <Box sx={{ display: "flex", justifyContent: "center" }}>
          <Button
            variant="text"
            size="small"
            onClick={toggleExpand}
            sx={{
              color: BCDesignTokens.themeBlue80,
              "&:hover": {
                backgroundColor: "rgba(85, 149, 217, 0.1)",
              },
            }}
          >
            {expanded ? "Read Less" : "Read More"}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default SearchDocumentCard;
