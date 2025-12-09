export type EpicSearchRole =
  | "viewer"
  | "admin"

export const EPIC_SEARCH_ROLE = Object.freeze<
  Record<EpicSearchRole, EpicSearchRole>
>({
  viewer: "viewer",
  admin: "admin"
});