import { AppBar, Button, Grid, Typography, Menu, MenuItem, Avatar, Box, CircularProgress } from "@mui/material";
import { BarChart, Person, Login, Logout } from "@mui/icons-material";
import { useState } from "react";
import EAO_Logo from "@/assets/images/EAO_Logo.png";
import { AppConfig } from "@/utils/config";
import { BCDesignTokens } from "epic.theme";
import { Link } from "@tanstack/react-router";
import useAuth from "@/hooks/useAuth";
import { LocationControl } from "@/components/Location";
import { useRoles } from "@/hooks/useRoles";
import { useNavigate } from "@tanstack/react-router";

export default function EAOAppBar() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, user, login, logout } = useAuth();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    handleUserMenuClose();
    await logout();
  };

  const { isAdmin, isViewer } = useRoles();

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
            {/* Stats & Metrics Button - only show when authenticated */}
            {isAuthenticated && (
              <>
                {isAdmin &&
                  <LocationControl compact />
                }
                <Button
                  variant="outlined"
                  startIcon={<BarChart />}
                  sx={{
                    borderColor: BCDesignTokens.themePrimaryBlue,
                    color: BCDesignTokens.themePrimaryBlue,
                    '&:hover': {
                      borderColor: BCDesignTokens.themeBlue70,
                      backgroundColor: BCDesignTokens.themeBlue10,
                    },
                  }}
                  onClick={() => {
                    if (isAdmin || isViewer) {
                      navigate({ to: "/stats" });
                    } else {
                      navigate({ to: "/unauthorized" });
                    }
                  }}
                >
                  Stats & Metrics
                </Button>
              </>
            )}

            {/* Authentication UI */}
            {isLoading ? (
              <CircularProgress size={24} />
            ) : isAuthenticated ? (
              <Box display="flex" alignItems="center" gap={1}>
                <Button
                  onClick={handleUserMenuOpen}
                  startIcon={<Avatar sx={{ width: 24, height: 24 }}>{user?.name?.charAt(0) || 'U'}</Avatar>}
                  sx={{ 
                    color: 'white',
                    textTransform: 'none',
                    '&:hover': {
                      backgroundColor: BCDesignTokens.themeBlue10,
                      color: BCDesignTokens.themePrimaryBlue,
                    }
                  }}
                >
                  {user?.name || 'User'}
                </Button>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleUserMenuClose}
                  anchorOrigin={{
                    vertical: 'bottom',
                    horizontal: 'right',
                  }}
                  transformOrigin={{
                    vertical: 'top',
                    horizontal: 'right',
                  }}
                >
                  <MenuItem onClick={handleUserMenuClose}>
                    <Link to="/profile" style={{ textDecoration: 'none', color: 'inherit' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Person fontSize="small" />
                        Profile
                      </Box>
                    </Link>
                  </MenuItem>
                  <MenuItem onClick={handleLogout}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Logout fontSize="small" />
                      Sign Out
                    </Box>
                  </MenuItem>
                </Menu>
              </Box>
            ) : (
              <Button
                variant="contained"
                startIcon={<Login />}
                onClick={login}
                sx={{
                  backgroundColor: BCDesignTokens.themePrimaryBlue,
                  color: 'white',
                  '&:hover': {
                    backgroundColor: BCDesignTokens.themeBlue70,
                  }
                }}
              >
                Sign In
              </Button>
            )}
          </Grid>
        </Grid>
      </AppBar>
    </>
  );
}
