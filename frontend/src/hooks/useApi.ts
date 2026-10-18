import { useMemo } from "react";
import { createApiClient, type DemoRole } from "@foodbridge/shared/api/client";
import { useDemoRole } from "../context/DemoRoleContext";

/** API client bound to the page role (DEV switcher may override). */
export function useApi(pageRole: DemoRole, recipientId?: number | null) {
  const { resolveRole, recipientId: ctxRecipientId } = useDemoRole();
  const role = resolveRole(pageRole);
  const rid = recipientId !== undefined ? recipientId : ctxRecipientId;

  return useMemo(
    () => createApiClient({ role, recipientId: rid }),
    [role, rid]
  );
}
