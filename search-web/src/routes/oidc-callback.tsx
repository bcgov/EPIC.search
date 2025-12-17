import { createFileRoute, Navigate, useLocation } from "@tanstack/react-router";
import { useAuth } from "react-oidc-context";
import { PageLoader } from "@/components/PageLoader";
import { useRoles } from "@/contexts/AuthContext";

export const Route = createFileRoute("/oidc-callback")({
  component: OidcCallback,
});

function OidcCallback() {
  const { isAuthenticated, isLoading, error } = useAuth();
  const location = useLocation();
  const { hasAnyRole } = useRoles();

  if (isLoading) return <PageLoader />;
  if (error) return <Navigate to="/error" />;

  if (isAuthenticated) {
    const redirectTo = (location as any).state?.redirectTo || (hasAnyRole ? "/search" : "/");
    return <Navigate to={redirectTo} replace />;
  }

  return <Navigate to="/" replace />;
}
