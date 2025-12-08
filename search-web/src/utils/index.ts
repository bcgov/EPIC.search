import { jwtDecode } from "jwt-decode";
import { AppConfig } from "./config";

export const getUserRolesFromToken = (token?: string) => {
  if (!token) return [];
  const tokenData: any = jwtDecode(token);
  const appName = AppConfig.clientId;
  return tokenData?.resource_access?.[appName]?.roles || [];
};
