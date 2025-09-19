import EAOAppBar from "@/components/Shared/EAOAppBar";
import PageNotFound from "@/components/Shared/PageNotFound";
import AuthMonitor from "@/components/Auth/AuthMonitor";
// import SideNavBar from "@/components/Shared/SideNavBar";
import { Box } from "@mui/system";
import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
// import { TanStackRouterDevtools } from "@tanstack/router-devtools";
import { AuthContextProps } from "react-oidc-context";
// import { BCDesignTokens } from "epic.theme";
type RouterContext = {
  authentication: AuthContextProps;
};

export const Route = createRootRouteWithContext<RouterContext>()({
  component: Layout,
  notFoundComponent: PageNotFound,
});

function Layout() {
  return (
    <>
      <AuthMonitor />
      <EAOAppBar />
      <Box
        display={"flex"}
        height={"calc(100vh - 88px)"}
        pt={"88px"}
        // bgcolor={BCDesignTokens.themeGray30}
      >
        {/* <SideNavBar /> */}
        <Box
          display={"flex"}
          flexDirection={"column"}
          flex={1}
          padding={"1rem"}
        >
          <Outlet />
        </Box>
      </Box>
      {/* <TanStackRouterDevtools /> */}
    </>
  );
}
