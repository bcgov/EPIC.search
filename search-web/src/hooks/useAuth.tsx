import { useAuth as useOidcAuth } from "react-oidc-context";
import { User } from "oidc-client-ts";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  preferred_username?: string;
  given_name?: string;
  family_name?: string;
  groups?: string[];
  roles?: string[];
}

export const useAuth = () => {
  const oidcAuth = useOidcAuth();

  const getUser = (): AuthUser | null => {
    if (!oidcAuth.user) return null;

    const profile = oidcAuth.user.profile;
    return {
      id: profile.sub || "",
      name: profile.name || profile.preferred_username || profile.email || "",
      email: profile.email || "",
      preferred_username: profile.preferred_username,
      given_name: profile.given_name,
      family_name: profile.family_name,
      groups: profile.groups as string[],
      roles: profile.roles as string[],
    };
  };

  const login = async () => {
    try {
      await oidcAuth.signinRedirect();
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await oidcAuth.signoutRedirect();
    } catch (error) {
      console.error("Logout failed:", error);
      throw error;
    }
  };

  const getAccessToken = (): string | null => {
    return oidcAuth.user?.access_token || null;
  };

  const isTokenExpired = (): boolean => {
    if (!oidcAuth.user) return true;
    const now = Math.floor(Date.now() / 1000);
    return (oidcAuth.user.expires_at || 0) <= now;
  };

  const refreshToken = async (): Promise<User | null> => {
    try {
      return await oidcAuth.signinSilent();
    } catch (error) {
      console.error("Token refresh failed:", error);
      return null;
    }
  };

  return {
    // OIDC auth state
    isLoading: oidcAuth.isLoading,
    isAuthenticated: oidcAuth.isAuthenticated && !isTokenExpired(),
    error: oidcAuth.error,
    
    // User data
    user: getUser(),
    rawUser: oidcAuth.user,
    
    // Auth methods
    login,
    logout,
    refreshToken,
    
    // Token methods
    getAccessToken,
    isTokenExpired,
    
    // Direct OIDC methods for advanced use
    signinRedirect: oidcAuth.signinRedirect,
    signoutRedirect: oidcAuth.signoutRedirect,
    signinSilent: oidcAuth.signinSilent,
  };
};

export default useAuth;