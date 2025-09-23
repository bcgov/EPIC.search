/* eslint-disable @typescript-eslint/no-explicit-any */
import { AppConfig, OidcConfig } from '@/utils/config'
import axios, { AxiosError, AxiosResponse } from 'axios'
import { User } from "oidc-client-ts"
import type { LocationData } from '@/contexts/LocationContext'

export type OnErrorType = (error: AxiosError) => void;
export type OnSuccessType = (data: any) => void;

const client = axios.create({ 
  baseURL: AppConfig.apiUrl,
  timeout: 330000, // 5.5 minutes - slightly longer than nginx proxy_read_timeout
  headers: {
    'Content-Type': 'application/json',
  }
});

function getUser(): User | null {
  try {
    const oidcStorage = sessionStorage.getItem(`oidc.user:${OidcConfig.authority}:${OidcConfig.client_id}`)
    if (!oidcStorage) {
        return null;
    }
    return User.fromStorageString(oidcStorage);
  } catch (error) {
    console.warn('Failed to get user from storage:', error);
    return null;
  }
}

function getLocationData(): LocationData | null {
  try {
    const locationStr = localStorage.getItem('epic_search_user_location');
    if (!locationStr) return null;
    
    const locationData = JSON.parse(locationStr);
    // Check if location data is not too old (24 hours)
    const now = Date.now();
    const locationTimestamp = new Date(locationData.timestamp).getTime();
    const locationAge = now - locationTimestamp;
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
    
    if (locationAge > maxAge) {
      localStorage.removeItem('epic_search_user_location');
      return null;
    }
    
    return locationData;
  } catch (error) {
    console.warn('Failed to get location data from storage:', error);
    return null;
  }
}

function isTokenExpired(user: User | null): boolean {
  if (!user) return true;
  const now = Math.floor(Date.now() / 1000);
  const expiresAt = user.expires_at || 0;
  // Consider token expired if it expires within the next 30 seconds
  return expiresAt <= (now + 30);
}

// Request interceptor to add auth token and location headers
client.interceptors.request.use(
  (config) => {
    const user = getUser();
    if (user?.access_token && !isTokenExpired(user)) {
      config.headers.Authorization = `Bearer ${user.access_token}`;
    }
    
    // Add location data to search requests
    if (config.url?.includes('/search')) {
      const locationData = getLocationData();
      if (locationData && config.data && typeof config.data === 'object') {
        config.data = {
          ...config.data,
          userLocation: {
            latitude: locationData.latitude,
            longitude: locationData.longitude,
            city: locationData.city,
            region: locationData.region,
            country: locationData.country,
            timestamp: new Date(locationData.timestamp).getTime()
          }
        };
      }
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle 401 errors and token refresh
client.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to get the auth context for silent renewal
        const oidcUser = getUser();
        if (!oidcUser) {
          console.warn('No user found for token refresh');
          throw new Error('No user session found');
        }

        // Create a new user manager for silent renewal
        const { UserManager } = await import('oidc-client-ts');
        const userManager = new UserManager({
          authority: OidcConfig.authority,
          client_id: OidcConfig.client_id,
          redirect_uri: OidcConfig.redirect_uri,
          response_type: OidcConfig.response_type,
          scope: OidcConfig.scope,
          automaticSilentRenew: OidcConfig.automaticSilentRenew,
          silent_redirect_uri: window.location.origin + '/silent-renew.html',
          silentRequestTimeoutInSeconds: 10
        });

        console.log('Attempting silent token renewal due to 401 error...');
        const renewedUser = await userManager.signinSilent();
        
        if (renewedUser?.access_token) {
          console.log('Token renewed successfully, retrying request');
          // Update the authorization header for the retry
          originalRequest.headers.Authorization = `Bearer ${renewedUser.access_token}`;
          return client(originalRequest);
        }
      } catch (renewError) {
        console.error('Token renewal failed:', renewError);
        
        // If we're on a protected route, redirect to login
        if (window.location.pathname.startsWith('/search') || 
            window.location.pathname.startsWith('/stats')) {
          console.log('Redirecting to login due to auth failure');
          window.location.href = '/';
        }
      }
    }

    // Handle other errors
    if (!error.response) {
      // CORS error or network error
      throw new Error('Network error or CORS issue');
    }
    
    throw error;
  }
);

export const request = ({ ...options }) => {
  const onSuccess = (response: any) => response
  const onError = (error: AxiosError) => {
    console.error('API request failed:', error);
    throw error;
  }

  return client(options).then(onSuccess).catch(onError)
}
