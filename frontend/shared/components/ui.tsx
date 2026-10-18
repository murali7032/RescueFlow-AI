import React, { useState } from "react";

export function PageHeader({
  title,
  subtitle,
  role,
  actions,
}: {
  title: string;
  subtitle?: string;
  role?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle ? <p className="muted">{subtitle}</p> : null}
      </div>
      <div className="topbar-right">
        {role ? <span className="role-chip">{role}</span> : null}
        {actions}
      </div>
    </header>
  );
}

/** @deprecated Prefer PageHeader inside AppShell — kept for compatibility */
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
    <div className="page">
      <PageHeader title={title} subtitle={subtitle} role={role} actions={actions} />
      <div className="content">{children}</div>
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
  loading = false,
  className,
}: {
  children: React.ReactNode;
  onClick?: () => unknown;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  type?: "button" | "submit";
  loading?: boolean;
  className?: string;
}) {
  const [pending, setPending] = useState(false);
  const isLoading = loading || pending;
  function handleClick() {
    if (!onClick || isLoading || disabled) return;
    const result = onClick();
    if (result && typeof (result as Promise<unknown>).then === "function") {
      setPending(true);
      void Promise.resolve(result).catch(() => undefined).finally(() => setPending(false));
    }
  }
  return (
    <button
      type={type}
      className={`btn btn-${variant} ${className ?? ""}`}
      onClick={handleClick}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
    >
      {isLoading ? <span className="button-spinner" aria-hidden="true" /> : null}
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

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
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

export function Loading({ children = "Loading…" }: { children?: React.ReactNode }) {
  return (
    <div className="empty" role="status" aria-live="polite">
      {children}
    </div>
  );
}
