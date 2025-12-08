import NoRoles from "@/components/Shared/NoRoles";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/unauthorized")({
  component: NoRoles,
});
