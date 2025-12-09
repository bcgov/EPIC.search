import { useRolesContext } from "@/contexts/AuthContext";
import { EPIC_SEARCH_ROLE } from "@/models/Role";

export function useRoles() {
  const { roles } = useRolesContext();

  return {
    roles,
    isAdmin: roles.includes(EPIC_SEARCH_ROLE.admin),
    isViewer: roles.includes(EPIC_SEARCH_ROLE.viewer),
    canSearch: roles.includes(EPIC_SEARCH_ROLE.admin) || roles.includes(EPIC_SEARCH_ROLE.viewer),
  };
}
