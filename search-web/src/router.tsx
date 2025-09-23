import { createRouter, RouterProvider } from "@tanstack/react-router";
import { AuthProvider, useAuth } from "react-oidc-context";
import { routeTree } from "@/routeTree.gen";
import { OidcConfig } from "@/utils/config";
import { LocationProvider } from "@/contexts/LocationContext";

// Create a new router instance
const router = createRouter({
  routeTree,
  context: {
    authentication: undefined! as ReturnType<typeof useAuth>,
  },
});

// Register the router instance for type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

function RouterWithAuth() {
  const auth = useAuth();
  
  return (
    <LocationProvider>
      <RouterProvider router={router} context={{ authentication: auth }} />
    </LocationProvider>
  )
}

export default function RouterProviderWithAuthContext() {
  return (
    <AuthProvider {...OidcConfig}>
      <RouterWithAuth />
    </AuthProvider>
  );
}
