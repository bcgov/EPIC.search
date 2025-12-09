import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import useAuth from "@/hooks/useAuth";
import { getUserRolesFromToken } from "@/utils";

interface AuthRolesContextType {
  roles: string[];
  refreshRoles: () => void;
}

const AuthRolesContext = createContext<AuthRolesContextType>({
  roles: [],
  refreshRoles: () => {},
});

export const AuthRolesProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { rawUser, getAccessToken } = useAuth();
  const [roles, setRoles] = useState<string[]>([]);

  const refreshRoles = () => {
    const token = getAccessToken();
    const userRoles = getUserRolesFromToken(token ?? undefined);
    setRoles(userRoles);
  };

  useEffect(() => {
    // refresh roles whenever user changes (after login)
    refreshRoles();
  }, [rawUser]);

  return (
    <AuthRolesContext.Provider value={{ roles, refreshRoles }}>
      {children}
    </AuthRolesContext.Provider>
  );
};

export const useRolesContext = () => useContext(AuthRolesContext);
