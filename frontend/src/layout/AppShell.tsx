import { NavLink, Outlet } from "react-router-dom";
import { useDemoRole } from "../context/DemoRoleContext";
import type { DemoRole } from "@foodbridge/shared/api/client";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/donor", label: "Donor Workspace" },
  { to: "/recipient", label: "Recipient Workspace" },
  { to: "/admin", label: "Admin Dashboard" },
] as const;

export function AppShell() {
  const {
    switcherEnabled,
    overrideRole,
    setOverrideRole,
    recipientId,
    setRecipientId,
  } = useDemoRole();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <p className="brand">RescueFlow AI</p>
          <p className="sidebar-product">FoodBridge</p>
          <p className="muted sidebar-tagline">
            Surplus recovery · allocated ≠ meals served
          </p>
        </div>

        <nav className="sidebar-nav" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={"end" in item ? item.end : false}
              className={({ isActive }) =>
                `nav-link${isActive ? " nav-link-active" : ""}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {switcherEnabled ? (
          <div className="sidebar-demo">
            <p className="sidebar-demo-title">Dev demo role</p>
            <p className="muted" style={{ fontSize: "0.75rem", margin: "0 0 0.5rem" }}>
              Disabled in production builds.
            </p>
            <label>
              API role override
              <select
                value={overrideRole ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setOverrideRole(v ? (v as DemoRole) : null);
                }}
              >
                <option value="">Use page default</option>
                <option value="donor">donor</option>
                <option value="recipient">recipient</option>
                <option value="admin">admin</option>
              </select>
            </label>
            <label>
              Recipient id
              <input
                type="number"
                min={1}
                placeholder="optional"
                value={recipientId ?? ""}
                onChange={(e) =>
                  setRecipientId(e.target.value ? Number(e.target.value) : null)
                }
              />
            </label>
          </div>
        ) : null}

        <footer className="sidebar-footer">
          Synthetic demo rows are labelled. Pickup confirmation is separate from
          allocation.
        </footer>
      </aside>

      <div className="layout-main">
        <Outlet />
      </div>
    </div>
  );
}
