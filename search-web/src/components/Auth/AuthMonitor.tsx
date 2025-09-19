import { useEffect } from 'react';
import { useAuth } from 'react-oidc-context';

/**
 * AuthMonitor component handles OIDC authentication events and token management.
 * This component should be included once in the app to monitor auth state.
 */
const AuthMonitor = () => {
  const auth = useAuth();

  useEffect(() => {
    if (!auth.events) return;

    // Handle token expiring event
    const unsubscribeTokenExpiring = auth.events.addAccessTokenExpiring(() => {
      console.log('Access token expiring, attempting silent renewal...');
      auth.signinSilent().catch((error) => {
        console.error('Silent token renewal failed:', error);
        // If silent renewal fails, we might want to redirect to login
        // but only if the user is currently on a protected route
        if (window.location.pathname.startsWith('/search') || 
            window.location.pathname.startsWith('/stats')) {
          console.log('Redirecting to login due to token renewal failure');
          auth.signinRedirect();
        }
      });
    });

    // Handle token expired event
    const unsubscribeTokenExpired = auth.events.addAccessTokenExpired(() => {
      console.log('Access token expired');
      // Try silent renewal first
      auth.signinSilent().catch((error) => {
        console.error('Silent token renewal failed after expiration:', error);
        // If on a protected route, redirect to login
        if (window.location.pathname.startsWith('/search') || 
            window.location.pathname.startsWith('/stats')) {
          console.log('Redirecting to login due to expired token');
          auth.signinRedirect();
        }
      });
    });

    // Handle silent renewal errors
    const unsubscribeSilentRenewError = auth.events.addSilentRenewError((error) => {
      console.error('Silent renewal error:', error);
      // If on a protected route, redirect to login
      if (window.location.pathname.startsWith('/search') || 
          window.location.pathname.startsWith('/stats')) {
        console.log('Redirecting to login due to silent renewal error');
        auth.signinRedirect();
      }
    });

    // Handle user session changed (e.g., logout in another tab)
    const unsubscribeUserSessionChanged = auth.events.addUserSessionChanged(() => {
      console.log('User session changed, checking authentication status');
      if (!auth.isAuthenticated && 
          (window.location.pathname.startsWith('/search') || 
           window.location.pathname.startsWith('/stats'))) {
        console.log('User session lost, redirecting to login');
        auth.signinRedirect();
      }
    });

    // Cleanup event listeners
    return () => {
      unsubscribeTokenExpiring();
      unsubscribeTokenExpired();
      unsubscribeSilentRenewError();
      unsubscribeUserSessionChanged();
    };
  }, [auth]);

  // This component doesn't render anything
  return null;
};

export default AuthMonitor;