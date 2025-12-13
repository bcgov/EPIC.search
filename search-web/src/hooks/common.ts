import { useMediaQuery, useTheme } from "@mui/material";
import { useEffect } from "react";

export const useIsMobile = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  return isMobile;
};

// useMounted is a useEffect with empty dependencies array
export const useMounted = (callback: () => void) => {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(callback, []);
};
