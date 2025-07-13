import { Box, Typography, Chip } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { Document } from "@/models/Search";
import { ArticleTwoTone } from "@mui/icons-material";

interface SearchPageGroupHeaderProps {
  pageNumber: string;
  chunks: Document[];
}

const SearchPageGroupHeader = ({ 
  pageNumber, 
  chunks
}: SearchPageGroupHeaderProps) => {
  // Calculate the relevance ranking for this page
  // Find the best (lowest) relevance score for chunks on this page
  const bestRelevanceScore = Math.min(...chunks.map(chunk => chunk.relevance_score || 0));
  
  // Find how this page ranks among all pages in the document
  // This would ideally be calculated at a higher level, but for now we'll show chunk count
  const chunkCount = chunks.length;
  const chunkText = chunkCount === 1 ? "chunk" : "chunks";

  return (
    <Box
      sx={{
        mb: 1.5,
        background: BCDesignTokens.themeGray10,
        padding: 1.5,
        borderRadius: 1.5,
        border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <ArticleTwoTone 
          color="primary" 
          sx={{ fontSize: 20 }} 
        />
        <Typography
          variant="subtitle1"
          sx={{
            color: BCDesignTokens.themeGray80,
            fontWeight: 600,
          }}
        >
          Page {pageNumber}
        </Typography>
        <Chip
          size="small"
          variant="outlined"
          color="primary"
          label={`${chunkCount} ${chunkText}`}
          sx={{
            fontSize: "0.75rem",
            height: "20px",
          }}
        />
      </Box>
      
      <Typography
        variant="caption"
        sx={{
          color: BCDesignTokens.themeGray60,
          fontSize: "0.75rem",
          fontStyle: "italic",
        }}
      >
        Relevance: {bestRelevanceScore.toFixed(2)}
      </Typography>
    </Box>
  );
};

export default SearchPageGroupHeader;
