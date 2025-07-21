import { Box, Typography, Button, Paper, IconButton, Tooltip } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { ArrowBack, Code, ContentCopy } from "@mui/icons-material";
import { SearchResponse } from "@/models/Search";
import { useState } from "react";

interface RawResponseViewerProps {
  searchResponse: SearchResponse;
  searchText: string;
  onBack: () => void;
}

const RawResponseViewer = ({ 
  searchResponse, 
  searchText, 
  onBack 
}: RawResponseViewerProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const jsonString = JSON.stringify(searchResponse, null, 2);
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };
  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        right: 0,
        width: "100%",
        height: "100vh",
        backgroundColor: "#ffffff",
        zIndex: 1300,
        display: "flex",
        flexDirection: "column",
        animation: "slideInRight 0.3s ease-out",
        "@keyframes slideInRight": {
          "0%": {
            transform: "translateX(100%)",
          },
          "100%": {
            transform: "translateX(0)",
          },
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 3,
          borderBottom: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
          backgroundColor: BCDesignTokens.themeBlue10,
        }}
      >
        <Button
          startIcon={<ArrowBack />}
          onClick={onBack}
          sx={{
            mb: 2,
            color: BCDesignTokens.themeBlue80,
            "&:hover": {
              backgroundColor: "rgba(85, 149, 217, 0.1)",
            },
          }}
        >
          Back to Search Results
        </Button>
        
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <Code color="primary" sx={{ fontSize: 32 }} />
          <Box>
            <Typography variant="h4" color={BCDesignTokens.themeBlue80}>
              Raw Search Response
            </Typography>
            <Typography variant="body2" color={BCDesignTokens.themeGray60}>
              Search query: "{searchText}"
            </Typography>
          </Box>
        </Box>
      </Box>

      {/* JSON Content */}
      <Box
        sx={{
          flex: 1,
          overflow: "auto",
          p: 3,
        }}
      >
        <Paper
          elevation={1}
          sx={{
            p: 2,
            backgroundColor: "#1e1e1e", // Dark background for code
            borderRadius: 2,
            overflow: "auto",
            position: "relative",
          }}
        >
          <Tooltip title={copied ? "Copied!" : "Copy to clipboard"}>
            <IconButton
              onClick={handleCopy}
              sx={{
                position: "absolute",
                top: 16,
                right: 16,
                backgroundColor: "rgba(255, 255, 255, 0.1)",
                color: "#d4d4d4",
                "&:hover": {
                  backgroundColor: "rgba(255, 255, 255, 0.2)",
                },
                zIndex: 1,
              }}
            >
              <ContentCopy />
            </IconButton>
          </Tooltip>
          <pre
            style={{
              margin: 0,
              color: "#d4d4d4", // Light text for dark background
              fontSize: "14px",
              fontFamily: "'Consolas', 'Monaco', 'Courier New', monospace",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              wordWrap: "break-word",
            }}
          >
            {JSON.stringify(searchResponse, null, 2)}
          </pre>
        </Paper>
      </Box>
    </Box>
  );
};

export default RawResponseViewer;
