import { Search as SearchIcon } from "@mui/icons-material";
import { Box, Container, Grid, Typography } from "@mui/material";
import { InputBase } from "@mui/material";
import { IconButton } from "@mui/material";
import { Paper } from "@mui/material";
import { createFileRoute } from "@tanstack/react-router";
import { BCDesignTokens } from "epic.theme";
import { useEffect, useState } from "react";
import { useSearchData } from "@/hooks/useSearch";
import { SearchResponse } from "@/models/Search";
import SearchDocumentCard from "@/components/App/SearchDocumentCard";
import SearchSkelton from "@/components/App/SearchSkelton";
export const Route = createFileRoute("/search")({
  component: Search,
});

function Search() {
  const [searchText, setSearchText] = useState("");
  const [searchableText, setSearchableText] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(
    null
  );

  const { data: searchData, isLoading, error } = useSearchData(searchableText);

  useEffect(() => {
    if (searchData) {
      console.log("searchData", searchData);
      setSearchResults(searchData as SearchResponse);
    }
  }, [searchData]);

  const onSubmitSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    console.log("searchText", searchText);
    setSearchableText(searchText);
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 1 }}>
      <Typography
        variant="h2"
        sx={{
          mb: 0,
          textAlign: "center",
          color: BCDesignTokens.themePrimaryBlue,
        }}
      >
        Document Search
      </Typography>
      <Typography
        variant="body1"
        sx={{ mb: 3, textAlign: "center", color: BCDesignTokens.themeBlue90 }}
      >
        Search for documents by entering a keyword or phrase below.
      </Typography>
      <Paper
        component="form"
        sx={{
          borderRadius: "16px",
          display: "flex",
          alignItems: "center",
          padding: "8px 16px",
          border: "1px solid",
          borderColor: BCDesignTokens.themeBlue10,
          boxShadow: "0px 2px 6px -2px rgb(0 0 0 / 33%)",
          "&:hover": {
            boxShadow: "0px 2px 18px 0px rgb(85 149 217 / 36%)",
          },
          "&:focus-within": {
            boxShadow: "0px 2px 18px 0px rgb(85 149 217 / 36%)",
          },
        }}
      >
        <InputBase
          sx={{ ml: 1, flex: 1, height: 64 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search text..."
          inputProps={{ "aria-label": "search text" }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onSubmitSearch(e);
            }
          }}
        />
        <IconButton
          type="button"
          sx={{ p: "10px" }}
          aria-label="search"
          size="large"
          onClick={onSubmitSearch}
        >
          <SearchIcon sx={{ fontSize: 30 }} />
        </IconButton>
      </Paper>

      <Box
        sx={{
          mt: 2,
          display: "flex",
          flexDirection: "column",
          alignContent: "center",
          alignItems: "center",
        }}
      >
        {isLoading && <SearchSkelton />}
        {error && <Typography>Error: {error.message}</Typography>}
        {searchResults?.result && (
          <>
            <Typography
              variant="body1"
              sx={{
                my: 1,
                background: BCDesignTokens.themeBlue10,
                padding: 2,
                borderRadius: 2,
              }}
            >
              {searchResults.result.response}
            </Typography>
            <Grid container spacing={2}>
              {searchResults?.result.documents.map((document) => (
                <Grid item xs={12} md={6} lg={4} key={document.document_id}>
                  <SearchDocumentCard document={document} />
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </Box>
    </Container>
  );
}
