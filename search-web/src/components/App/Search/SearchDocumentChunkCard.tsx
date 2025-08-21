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
    if (!searchTerm.trim()) return text;

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
  };

  return (
    <Box
      sx={{
        my: 1,
        background: BCDesignTokens.themeBlue10,
        padding: 2,
        borderRadius: 2,
        height: expanded ? "auto" : 260,
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
            backgroundColor: "rgba(255, 255, 255, 0.95)",
            "&:hover": {
              backgroundColor: "rgba(255, 255, 255, 1)",
            },
            width: 32,
            height: 32,
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
        <DescriptionTwoTone color="primary" sx={{ fontSize: 20 }} />
        <Chip
          size="small"
          color="primary"
          variant="outlined"
          label={`Page ${document.page_number}`}
          sx={{
            fontWeight: "bold",
            my: 0.75,
            borderRadius: 1.5,
          }}
        />
      </Box>
      <Box
        sx={{
          position: "relative",
          overflow: "hidden",
          height: expanded ? "auto" : "150px",
          transition: "height 0.3s ease",
          flex: 1,
        }}
      >
        <Typography
          ref={contentRef}
          variant="body2"
          color={BCDesignTokens.themeGray80}
        >
          " {highlightSearchText(document.content, searchText)} "
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

export default SearchDocumentChunkCard;
