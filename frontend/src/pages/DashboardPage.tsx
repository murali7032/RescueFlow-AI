import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "@foodbridge/shared/api/client";
import {
  Banner,
  Button,
  Card,
  Empty,
  Loading,
  PageHeader,
  Stat,
} from "@foodbridge/shared/components/ui";
import type { AdminDashboard } from "@foodbridge/shared/types";
import { useApi } from "../hooks/useApi";

export default function DashboardPage() {
  const api = useApi("admin");
  const [dash, setDash] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const d = await api.get<AdminDashboard>("/api/v1/admin/dashboard");
      setDash(d);
      setMessage(null);
    } catch (err) {
      setDash(null);
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Failed to load dashboard",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function seed(force = false) {
    setMessage(null);
    try {
      const result = await api.post<{ message: string; count: number; label?: string }>(
        `/api/v1/demo/seed?force=${force}`
      );
      setMessage({
        tone: "success",
        text: `${result.label ?? "Demo"}: ${result.message} (${result.count} recipients)`,
      });
      await load();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Seed failed",
      });
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Dashboard"
        subtitle="Live metrics from the API. Allocated portions are reserved stock — not meals served until pickup is completed."
        role="Overview"
        actions={
          <>
            <Button variant="secondary" onClick={() => seed(false)}>
              Seed demo
            </Button>
            <Button variant="ghost" onClick={() => load()}>
              Refresh
            </Button>
          </>
        }
      />

      <div className="content">
        {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}

        <Banner tone="warn">
          Allocated ≠ pickup confirmed ≠ pickup completed. Only completed pickups
          count as meals handed off.
        </Banner>

        {loading ? <Loading>Loading dashboard metrics…</Loading> : null}

        {!loading && !dash && !message ? (
          <Empty>No dashboard data yet. Seed demo data to begin.</Empty>
        ) : null}

        {dash ? (
          <Card title="Persisted metrics" tone="accent">
            <p className="muted">{dash.label}</p>
            <div className="stats">
              <Stat label="Donations" value={dash.total_donations} />
              <Stat label="Portions donated" value={dash.total_portions_donated} />
              <Stat
                label="Allocated"
                value={dash.portions_allocated}
                hint="Reserved, not served"
              />
              <Stat
                label="Pickup confirmed"
                value={dash.portions_pickup_confirmed}
                hint="Confirmed or completed"
              />
              <Stat
                label="Pickup completed"
                value={dash.portions_pickup_completed}
                hint="Meals handed off"
              />
              <Stat label="Pending invites" value={dash.pending_invitations} />
              <Stat label="Need recovery" value={dash.donations_needing_recovery} />
            </div>
            <p className="muted">{dash.note}</p>
          </Card>
        ) : null}

        <Card title="Workspaces">
          <div className="grid-3">
            <Link className="workspace-tile" to="/donor">
              <strong>Donor Workspace</strong>
              <span className="muted">Publish surplus and review ranked offers</span>
            </Link>
            <Link className="workspace-tile" to="/recipient">
              <strong>Recipient Workspace</strong>
              <span className="muted">Accept, decline, confirm pickup</span>
            </Link>
            <Link className="workspace-tile" to="/admin">
              <strong>Admin Dashboard</strong>
              <span className="muted">Recovery queue, audit, full metrics</span>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
