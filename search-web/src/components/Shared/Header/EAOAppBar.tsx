import { AppBar, Grid, Typography, Box, Divider } from "@mui/material";
import EAO_Logo from "@/assets/images/EAO_Logo.png";
import { AppConfig } from "@/utils/config";
import { BCDesignTokens } from "epic.theme";
import useAuth from "@/hooks/useAuth";
import { useIsMobile } from "@/hooks/common";
import AppBarActions from "./AppBarActions";

export default function EAOAppBar() {
  const isMobile = useIsMobile();
  const { login } = useAuth();

  return (
    <>
      <AppBar
        position="fixed"
        color="inherit"
        sx={{
          borderBottom: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
          boxShadow: "none",
        }}
      >
        <Grid
          container
          marginY={BCDesignTokens.layoutMarginSmall}
          paddingX={isMobile ? 0 : "0.5rem"}
          justifyContent="space-between"
        >
          <Box
            display="flex"
            justifyContent="start"
            alignItems="center"
            onClick={login}
            sx={{
              cursor: "pointer",
            }}
          >
            <img src={EAO_Logo} height={isMobile ? 40 : 56} />
            {!isMobile && (
              <>
                <Divider orientation="vertical" flexItem sx={{ m: 1 }} />
                <Typography
                  variant="h2"
                  color="inherit"
                  component="div"
                  paddingLeft={"0.5rem"}
                  fontWeight={"bold"}
                >
                  {AppConfig.appTitle || "EPIC.centre"}
                </Typography>
              </>
            )}
          </Box>

          <Grid
            display="flex"
            justifyContent="center"
            alignItems="center"
            paddingRight={"0.75rem"}
          >
            <AppBarActions />
          </Grid>
        </Grid>
      </AppBar>
    </>
  );
}
