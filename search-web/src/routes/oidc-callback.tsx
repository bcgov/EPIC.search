import { createFileRoute, Navigate } from "@tanstack/react-router";
import { useAuth } from "react-oidc-context";
import { useEffect } from "react";

export const Route = createFileRoute("/oidc-callback")({
  component: OidcCallback,
});

function OidcCallback() {
  const { isAuthenticated, isLoading, error, user } = useAuth();

  useEffect(() => {
    console.log('OIDC Callback - isLoading:', isLoading);
    console.log('OIDC Callback - isAuthenticated:', isAuthenticated);
    console.log('OIDC Callback - error:', error);
    console.log('OIDC Callback - user:', user);
  }, [isLoading, isAuthenticated, error, user]);

  if (isLoading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h1>Processing authentication...</h1>
        <p>Please wait while we complete the sign-in process.</p>
      </div>
    );
  }

  if (error?.message) {
    console.error('OIDC Authentication Error:', error);
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h1>Authentication Error</h1>
        <p><strong>Error:</strong> {error.message}</p>
        <details style={{ marginTop: '20px', textAlign: 'left' }}>
          <summary>Debug Information</summary>
          <pre style={{ background: '#f5f5f5', padding: '10px', fontSize: '12px' }}>
            {JSON.stringify(error, null, 2)}
          </pre>
        </details>
        <button onClick={() => window.location.href = '/'} style={{ marginTop: '20px' }}>
          Return to Home
        </button>
      </div>
    );
  }

  if (!isLoading && isAuthenticated) {
    console.log('OIDC Callback - Successfully authenticated, redirecting to home');
    return <Navigate to="/" />;
  }

  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>Authentication Status Unknown</h1>
      <p>Please try signing in again.</p>
      <button onClick={() => window.location.href = '/'}>
        Return to Home
      </button>
    </div>
  );
}
