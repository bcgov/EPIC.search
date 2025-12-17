import {
  Box,
  Typography,
  Button,
  Menu,
  IconButton,
  MenuItem,
} from "@mui/material";
import { useAuth } from "react-oidc-context";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { theme } from "@/styles/theme";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { useState } from "react";
import { OidcConfig } from "@/utils/config";
import { BCDesignTokens } from "epic.theme";

export default function AppBarActions() {
  const auth = useAuth();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogin = () => {
    setAnchorEl(null);
    auth.signinRedirect({
      redirect_uri: `${OidcConfig.redirect_uri}${window.location.search}`,
      prompt: "login",
    });
  };

  return (
    <>
      {auth.isAuthenticated ? (
        <>
          <Box id="menu-appbar" display="flex" alignItems="center">
            <Typography
              variant="body2"
              color="primary"
              onClick={handleClick}
              sx={{ cursor: "pointer" }}
            >
              Hi, {auth.user?.profile.given_name}
            </Typography>
            <IconButton size="small" onClick={handleClick}>
              <KeyboardArrowDownIcon
                fontSize="small"
                htmlColor={theme.palette.grey[900]}
              />
            </IconButton>
            <AccountCircleIcon
              fontSize="large"
              htmlColor={theme.palette.grey[900]}
              sx={{ ml: 0.5 }}
            />
          </Box>
          <Menu
            open={open}
            anchorEl={anchorEl}
            onClose={handleClose}
            anchorOrigin={{ vertical: "top", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <MenuItem
              onClick={() => {
                handleClose();
                auth.signoutRedirect({
                  post_logout_redirect_uri: window.location.origin,
                });
              }}
            >
              Sign Out
            </MenuItem>
          </Menu>
        </>
      ) : (
        <Button
          variant="text"
          onClick={handleLogin}
          sx={{
            color: BCDesignTokens.themeGray100,
            border: `2px solid ${theme.palette.grey[700]}`,
            visibility: open ? "hidden" : "visible",
          }}
        >
          Login
        </Button>
      )}
    </>
  );
}
