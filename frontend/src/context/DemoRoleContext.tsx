import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { DemoRole } from "@foodbridge/shared/api/client";

/** True only in Vite `npm run dev` — never in production builds. */
export const isDemoRoleSwitcherEnabled = import.meta.env.DEV === true;

type DemoRoleContextValue = {
  /** Page-default role unless a DEV override is set. */
  resolveRole: (pageRole: DemoRole) => DemoRole;
  overrideRole: DemoRole | null;
  setOverrideRole: (role: DemoRole | null) => void;
  recipientId: number | null;
  setRecipientId: (id: number | null) => void;
  switcherEnabled: boolean;
};

const DemoRoleContext = createContext<DemoRoleContextValue | null>(null);

export function DemoRoleProvider({ children }: { children: ReactNode }) {
  const [overrideRole, setOverrideRoleState] = useState<DemoRole | null>(null);
  const [recipientId, setRecipientId] = useState<number | null>(null);

  const setOverrideRole = useCallback((role: DemoRole | null) => {
    if (!isDemoRoleSwitcherEnabled) return;
    setOverrideRoleState(role);
  }, []);

  const resolveRole = useCallback(
    (pageRole: DemoRole) => {
      if (isDemoRoleSwitcherEnabled && overrideRole) return overrideRole;
      return pageRole;
    },
    [overrideRole]
  );

  const value = useMemo(
    () => ({
      resolveRole,
      overrideRole,
      setOverrideRole,
      recipientId,
      setRecipientId,
      switcherEnabled: isDemoRoleSwitcherEnabled,
    }),
    [resolveRole, overrideRole, setOverrideRole, recipientId]
  );

  return (
    <DemoRoleContext.Provider value={value}>{children}</DemoRoleContext.Provider>
  );
}

export function useDemoRole() {
  const ctx = useContext(DemoRoleContext);
  if (!ctx) throw new Error("useDemoRole must be used within DemoRoleProvider");
  return ctx;
}
