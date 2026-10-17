import React from "react";

export function Shell({
  title,
  subtitle,
  role,
  children,
  actions,
}: {
  title: string;
  subtitle?: string;
  role: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="brand">RescueFlow AI</p>
          <h1>{title}</h1>
          {subtitle ? <p className="muted">{subtitle}</p> : null}
        </div>
        <div className="topbar-right">
          <span className="role-chip">{role}</span>
          {actions}
        </div>
      </header>
      <main className="content">{children}</main>
      <footer className="footer">
        FoodBridge · Synthetic demo data is labelled · Allocated ≠ meals served
      </footer>
    </div>
  );
}

export function Card({
  title,
  children,
  tone = "default",
}: {
  title?: string;
  children: React.ReactNode;
  tone?: "default" | "accent" | "warn";
}) {
  return (
    <section className={`card card-${tone}`}>
      {title ? <h2>{title}</h2> : null}
      {children}
    </section>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  type = "button",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  return (
    <button
      type={type}
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Banner({
  children,
  tone = "info",
}: {
  children: React.ReactNode;
  tone?: "info" | "success" | "error" | "warn";
}) {
  return <div className={`banner banner-${tone}`}>{children}</div>;
}

export function Stat({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {hint ? <span className="muted">{hint}</span> : null}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}
