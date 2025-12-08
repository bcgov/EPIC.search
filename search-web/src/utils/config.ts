declare global {
  interface Window {
    _env_: {
      VITE_API_URL: string;
      VITE_VERSION: string;
      VITE_APP_TITLE: string;
      VITE_APP_URL: string;
      VITE_OIDC_AUTHORITY: string;
      VITE_CLIENT_ID: string;
    };
  }
}
const API_URL =
  window._env_?.VITE_API_URL || import.meta.env.VITE_API_URL || "/api";

const APP_VERSION =
  window._env_?.VITE_VERSION || import.meta.env.VITE_VERSION || "";
const APP_TITLE =
  window._env_?.VITE_APP_TITLE || import.meta.env.VITE_APP_TITLE || "";
const APP_URL = window._env_?.VITE_APP_URL || import.meta.env.VITE_APP_URL;
const OIDC_AUTHORITY = window._env_?.VITE_OIDC_AUTHORITY || import.meta.env.VITE_OIDC_AUTHORITY;
const CLIENT_ID = window._env_?.VITE_CLIENT_ID || import.meta.env.VITE_CLIENT_ID;

export const AppConfig = {
  apiUrl: `${API_URL}`,
  version: APP_VERSION,
  appTitle: APP_TITLE,
  clientId: CLIENT_ID,
};

export const OidcConfig = {
  authority: OIDC_AUTHORITY,
  client_id: CLIENT_ID,
  redirect_uri: `${APP_URL}/oidc-callback`,
  post_logout_redirect_uri: `${APP_URL}/`,
  response_type: "code",
  scope: "openid profile email",
  revokeTokensOnSignout: true,
  automaticSilentRenew: true,
  loadUserInfo: false,
  monitorSession: true,
  checkSessionInterval: 30000, // Check every 30 seconds
  silentRequestTimeoutInSeconds: 10,
  accessTokenExpiringNotificationTimeInSeconds: 60, // Notify 1 minute before expiration
};
