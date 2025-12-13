import { createFileRoute } from "@tanstack/react-router";
import { Button, Paper } from "@mui/material";
import { useAuth } from "react-oidc-context";
import { OidcConfig } from "@/utils/config";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() { 
  const auth = useAuth();

  const handleLogin = () => {
    auth.signinRedirect({
      redirect_uri: `${OidcConfig.redirect_uri}${window.location.search}`,
      prompt: "login",
    });
  };

  return (
    <>
      <Paper
        elevation={2}
        sx={{
          padding: "6rem 0rem 2.5rem 2.5rem",
          backgroundColor: "primary.accent.light",
        }}
      >
        <h2>Environmental Assessments</h2>
        <p>
          British Columbia's environmental assessment process provides
          opportunities for Indigenous Nations, government agencies and the
          public to influence the outcome of environmental assessments in
          British Columbia.
        </p>
        <Button
          variant="outlined"
          color="primary"
          onClick={handleLogin}
        >
          Sign In to Search
        </Button>
      </Paper>
    </>
  );
}

