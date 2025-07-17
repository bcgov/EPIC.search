import { Box, CircularProgress, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";

const ProjectLoadingScreen = () => (
  <Box
    sx={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      minHeight: 320,
      gap: 3,
      width: "100%",
      py: 6,
    }}
  >
    <CircularProgress size={48} thickness={4} sx={{ color: BCDesignTokens.themePrimaryBlue }} />
    <Typography variant="h5" color={BCDesignTokens.themePrimaryBlue}>
      Getting things ready…
    </Typography>
    <Typography variant="body2" color={BCDesignTokens.themeGray70}>
      This may take a few seconds...
    </Typography>
  </Box>
);

export default ProjectLoadingScreen;
