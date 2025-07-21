import { AppBar, Button, Grid, Typography } from "@mui/material";
import { BarChart } from "@mui/icons-material";
import EAO_Logo from "@/assets/images/EAO_Logo.png";
import { AppConfig } from "@/utils/config";
import { BCDesignTokens } from "epic.theme";
import { Link, useLocation } from "@tanstack/react-router";

export default function EAOAppBar() {
  const location = useLocation();
  return (
    <>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={2}
        sx={{ backgroundColor: BCDesignTokens.themeGray10 }}
      >
        <Grid
          container
          padding={"0.5rem"}
          margin={0}
          justifyContent="space-between"
          alignItems="center"
        >
          <Grid display="flex" justifyContent="start" alignItems="center">
            <img src={EAO_Logo} height={72} />
            <Typography
              variant="h2"
              color="inherit"
              component="div"
              paddingLeft={"0.5rem"}
              fontWeight={"bold"}
            >
              {AppConfig.appTitle}
            </Typography>
          </Grid>

          <Grid
            display="flex"
            justifyContent="flex-end"
            alignItems="center"
            gap={2}
            paddingRight={"0.75rem"}
          >
            {/* Stats & Metrics Button - only show on search route */}
            {location.pathname === '/search' && (
              <Link to="/stats">
                <Button
                  variant="outlined"
                  startIcon={<BarChart />}
                  sx={{ 
                    borderColor: BCDesignTokens.themePrimaryBlue,
                    color: BCDesignTokens.themePrimaryBlue,
                    '&:hover': {
                      borderColor: BCDesignTokens.themeBlue70,
                      backgroundColor: BCDesignTokens.themeBlue10,
                    }
                  }}
                >
                  Stats & Metrics
                </Button>
              </Link>
            )}
          </Grid>
        </Grid>
      </AppBar>
    </>
  );
}
