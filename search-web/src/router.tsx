import { createRouter, RouterProvider } from "@tanstack/react-router";
import { routeTree } from "@/routeTree.gen";

// Create a new router instance
const router = createRouter({
  routeTree,
  context: {
    // Provide a mock authentication context since we're disabling OIDC
    authentication: {
      isAuthenticated: false,
      user: null,
      signinRedirect: () => console.log('Authentication disabled'),
      signoutRedirect: () => console.log('Authentication disabled'),
    } as any,
  },
});

// Register the router instance for type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default function RouterProviderWithAuthContext() {
  // Always provide mock auth since OIDC is disabled
  const mockAuth = {
    isAuthenticated: false,
    user: null,
    signinRedirect: () => console.log('Authentication disabled'),
    signoutRedirect: () => console.log('Authentication disabled'),
  } as any;
  
  return <RouterProvider router={router} context={{ authentication: mockAuth }} />
}
