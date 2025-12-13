import EAOAppBar from "@/components/Shared/Header/EAOAppBar";
import PageNotFound from "@/components/Shared/PageNotFound";
import AuthMonitor from "@/components/Auth/AuthMonitor";
// import SideNavBar from "@/components/Shared/SideNavBar";
import { Box } from "@mui/system";
import {
  CatchBoundary,
  createRootRouteWithContext,
  Outlet,
  useNavigate
} from "@tanstack/react-router";
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
  const navigate = useNavigate();

  return (
    <CatchBoundary
      getResetKey={() => "reset"}
      onCatch={() => navigate({ to: "/error" })}
    >
      <AuthMonitor />
      <EAOAppBar />
      <Box>
        <Outlet />
      </Box>
      {/* <TanStackRouterDevtools /> */}
    </CatchBoundary>
  );
}
