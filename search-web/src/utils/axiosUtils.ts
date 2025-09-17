/* eslint-disable @typescript-eslint/no-explicit-any */
import { AppConfig, OidcConfig } from '@/utils/config'
import axios, { AxiosError } from 'axios'
import { User } from "oidc-client-ts"

export type OnErrorType = (error: AxiosError) => void;
export type OnSuccessType = (data: any) => void;

const client = axios.create({ baseURL: AppConfig.apiUrl });

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

export const request = ({ ...options }) => {
  
  const user = getUser();
  
  if(user?.access_token) {
    client.defaults.headers.common.Authorization = `Bearer ${user?.access_token}`
  }
  // Note: Removed the error throw to allow non-authenticated requests
  // Some endpoints might not require authentication
  
  const onSuccess = (response: any) => response
  const onError = (error: AxiosError) => {
    // optionaly catch errors and add additional logging here
    if (!error.response) {
      // CORS error or network error
      throw new Error('Network error or CORS issue');
    }
    throw error
  }

  return client(options).then(onSuccess).catch(onError)
}
