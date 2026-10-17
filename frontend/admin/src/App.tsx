import { useEffect, useMemo, useState } from "react";
import { ApiError, createApiClient } from "@foodbridge/shared/api/client";
import { Banner, Button, Card, Empty, Shell, Stat } from "@foodbridge/shared/components/ui";
import type { AdminDashboard } from "@foodbridge/shared/types";

interface RecoveryPayload {
  count: number;
  total_remaining_portions_at_risk: number;
  donations_needing_recovery: Array<{
    donation_id: number;
    donor_name: string;
    remaining_portions: number;
    declined_invitations: number;
    pending_invitations: number;
    needs_recovery: boolean;
    is_demo?: boolean;
  }>;
  recent_recovery_events: Array<{
    id: number;
    action: string;
    entity_id: string;
    created_at?: string;
  }>;
}

interface AuditEvent {
  id: number;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  created_at?: string;
}

export default function App() {
  const api = useMemo(() => createApiClient({ role: "admin" }), []);
  const [dash, setDash] = useState<AdminDashboard | null>(null);
  const [recovery, setRecovery] = useState<RecoveryPayload | null>(null);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [aiSummary, setAiSummary] = useState<string>("");
  const [message, setMessage] = useState<{ tone: "success" | "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadAll() {
    const [d, r, a] = await Promise.all([
      api.get<AdminDashboard>("/api/v1/admin/dashboard"),
      api.get<RecoveryPayload>("/api/v1/admin/recovery"),
      api.get<AuditEvent[]>("/api/v1/admin/audit-events?limit=20"),
    ]);
    setDash(d);
    setRecovery(r);
    setAudit(a);
  }

  useEffect(() => {
    loadAll().catch((e) =>
      setMessage({ tone: "error", text: e instanceof Error ? e.message : "Load failed" })
    );
  }, []);

  async function seed(force = false) {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.post<{ message: string; count: number; label?: string }>(
        `/api/v1/demo/seed?force=${force}`
      );
      setMessage({
        tone: "success",
        text: `${result.label ?? "Demo"}: ${result.message} (${result.count} recipients)`,
      });
      await loadAll();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Seed failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function runRecovery(donationId: number) {
    setBusy(true);
    try {
      const result = await api.post<{ new_invitations: number }>(
        `/api/v1/admin/recovery/${donationId}`
      );
      setMessage({
        tone: "success",
        text: `Recovery rematch created ${result.new_invitations} invitation(s).`,
      });
      await loadAll();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Recovery failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function loadAiSummary() {
    setBusy(true);
    try {
      const result = await api.get<{ source: string; summary: string }>(
        "/api/v1/ai/recovery-summary"
      );
      setAiSummary(`(${result.source}) ${result.summary}`);
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "AI summary unavailable",
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell
      title="Operations dashboard"
      subtitle="Monitor allocation vs pickup, declines, and recovery activity from live API data."
      role="Administrator"
      actions={
        <>
          <Button variant="secondary" disabled={busy} onClick={() => seed(false)}>
            Seed demo
          </Button>
          <Button variant="ghost" disabled={busy} onClick={() => seed(true)}>
            Reset & reseed
          </Button>
        </>
      }
    >
      {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}
      <Banner tone="warn">
        Synthetic demo data only. Allocated portions are not meals served until pickup is completed.
      </Banner>

      {dash ? (
        <Card title="Impact & flow metrics" tone="accent">
          <p className="muted">{dash.label}</p>
          <div className="stats">
            <Stat label="Donations" value={dash.total_donations} />
            <Stat label="Portions donated" value={dash.total_portions_donated} />
            <Stat label="Allocated" value={dash.portions_allocated} hint="Reserved, not served" />
            <Stat label="Pickup confirmed" value={dash.portions_pickup_confirmed} />
            <Stat label="Pickup completed" value={dash.portions_pickup_completed} />
            <Stat label="Pending invites" value={dash.pending_invitations} />
            <Stat label="Declined" value={dash.declined_invitations} />
            <Stat label="Need recovery" value={dash.donations_needing_recovery} />
            <Stat label="Recovery rate %" value={dash.recovery_rate_percent} />
          </div>
          <p className="muted">{dash.note}</p>
        </Card>
      ) : (
        <Empty>Loading dashboard…</Empty>
      )}

      <div className="grid-2">
        <Card title="Donations needing recovery">
          <div className="row-actions" style={{ marginBottom: "0.75rem" }}>
            <Button variant="secondary" disabled={busy} onClick={loadAiSummary}>
              AI recovery summary
            </Button>
            <Button variant="ghost" disabled={busy} onClick={() => loadAll()}>
              Refresh
            </Button>
          </div>
          {aiSummary ? <Banner tone="info">{aiSummary}</Banner> : null}
          {!recovery?.donations_needing_recovery?.length ? (
            <Empty>No donations currently flagged for recovery.</Empty>
          ) : (
            <div className="list">
              {recovery.donations_needing_recovery.map((d) => (
                <div key={d.donation_id} className="list-item">
                  <header>
                    <strong>
                      #{d.donation_id} · {d.donor_name}
                    </strong>
                    {d.is_demo ? <span className="badge badge-demo">Demo</span> : null}
                  </header>
                  <div>
                    Remaining {d.remaining_portions} · Declines {d.declined_invitations} ·
                    Pending {d.pending_invitations}
                  </div>
                  {d.needs_recovery ? (
                    <Button disabled={busy} onClick={() => runRecovery(d.donation_id)}>
                      Rematch now
                    </Button>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Recent audit events">
          {audit.length === 0 ? (
            <Empty>No audit events yet.</Empty>
          ) : (
            <div className="list">
              {audit.map((e) => (
                <div key={e.id} className="list-item">
                  <header>
                    <strong>{e.action}</strong>
                    <span className="badge">
                      {e.entity_type}:{e.entity_id}
                    </span>
                  </header>
                  <div className="muted">{e.created_at}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </Shell>
  );
}
