import { Box, Button, Chip, Link, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { useState, useRef, useEffect } from "react";
import { DescriptionTwoTone } from "@mui/icons-material";
import { AppConfig } from '@/utils/config';

interface SearchDocumentCardProps {
  document: Document;
  searchText: string;
}

const SearchDocumentCard = ({
  document,
  searchText,
}: SearchDocumentCardProps) => {
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
      }}
    >
      <Link 
        href="#"        
        underline="none" 
        sx={{ fontWeight: "bold" }}
        onClick={async (e) => {
          e.preventDefault();
          
          try {
            const encodedKey = encodeURIComponent(document.s3_key);
            const encodedFileName = encodeURIComponent(document.document_saved_name);
            const response = await fetch(
              `${AppConfig.apiUrl}/document/view?key=${encodedKey}&file_name=${encodedFileName}`, 
              {
                method: 'GET',
                headers: {
                  'Accept': 'application/pdf',
                }
              }
            );

            if (!response.ok) {
              throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }

            const blob = await response.blob();
            const pdfBlob = new Blob([blob], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(pdfBlob) + `#page=${document.page_number}`;
            
            // Open PDF directly in new tab
            window.open(url, '_blank');
            
            // Clean up the blob URL after a delay
            setTimeout(() => {
              window.URL.revokeObjectURL(url.split('#')[0]);
            }, 1000);

          } catch (error) {
            console.error('Error:', error);
          }
        }}
      >
        {document.document_saved_name}
      </Link>
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

export default SearchDocumentCard;
