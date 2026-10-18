import { useEffect, useState } from "react";
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

interface DonorReview {
  id: number;
  donor_name: string;
  donation_id: number;
  food_name: string | null;
  recipient_name: string | null;
  rating: number;
  feedback: string;
  created_at?: string;
}

export default function AdminDashboardPage() {
  const api = useApi("admin");
  const [dash, setDash] = useState<AdminDashboard | null>(null);
  const [recovery, setRecovery] = useState<RecoveryPayload | null>(null);
  const [reviews, setReviews] = useState<DonorReview[]>([]);
  const [aiSummary, setAiSummary] = useState<string>("");
  const [aiSource, setAiSource] = useState<string>("");
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    try {
      const [d, r, reviews] = await Promise.all([
        api.get<AdminDashboard>("/api/v1/admin/dashboard"),
        api.get<RecoveryPayload>("/api/v1/admin/recovery"),
        api.get<DonorReview[]>("/api/v1/admin/donor-reviews?limit=20"),
      ]);
      setDash(d);
      setRecovery(r);
      setReviews(reviews);
      setMessage(null);
    } catch (e) {
      setMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "Load failed",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function seed(force = false) {
    setBusy(true);
    setBusyAction(force ? "seed-reset" : "seed");
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
      setBusyAction(null);
    }
  }

  async function runRecovery(donationId: number) {
    setBusy(true);
    setBusyAction(`recovery-${donationId}`);
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
      setBusyAction(null);
    }
  }

  async function loadAiSummary() {
    setBusy(true);
    setBusyAction("ai-summary");
    setAiSummary("");
    setAiSource("");
    setMessage(null);
    try {
      const result = await api.get<{ source: "gemini"; summary: string; context?: RecoveryPayload }>(
        "/api/v1/ai/recovery-summary"
      );
      setAiSummary(result.summary.trim());
      setAiSource("Gemini");
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "AI summary unavailable",
      });
    } finally {
      setBusy(false);
      setBusyAction(null);
    }
  }

  return (
    <div className="page">
      <PageHeader
        title="Admin dashboard"
        subtitle="Monitor allocation vs pickup, declines, and recovery activity from live API data."
        role="Administrator"
        actions={
          <>
            <Button variant="secondary" disabled={busy && busyAction !== "seed"} loading={busyAction === "seed"} onClick={() => seed(false)}>
              Seed demo
            </Button>
            <Button variant="ghost" disabled={busy && busyAction !== "seed-reset"} loading={busyAction === "seed-reset"} onClick={() => seed(true)}>
              Reset & reseed
            </Button>
          </>
        }
      />

      <div className="content">
        {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}
        <Banner tone="warn">
          Synthetic demo data only. Allocated portions are not meals served until
          pickup is completed.
        </Banner>

        {loading ? <Loading>Loading admin data…</Loading> : null}

        {!loading && dash ? (
          <Card title="Impact & flow metrics" tone="accent">
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
              />
              <Stat
                label="Pickup completed"
                value={dash.portions_pickup_completed}
                hint="Meals handed off"
              />
              <Stat label="Pending invites" value={dash.pending_invitations} />
              <Stat label="Declined" value={dash.declined_invitations} />
              <Stat label="Need recovery" value={dash.donations_needing_recovery} />
              <Stat label="Recovery rate %" value={dash.recovery_rate_percent} />
            </div>
            <p className="muted">{dash.note}</p>
          </Card>
        ) : null}

        {!loading && !dash && !message ? (
          <Empty>No admin metrics yet. Seed demo data to populate the dashboard.</Empty>
        ) : null}

        <div className="grid-2">
          <Card title="Donations needing recovery">
            <div className="row-actions" style={{ marginBottom: "0.75rem" }}>
              <Button variant="secondary" disabled={busy && busyAction !== "ai-summary"} loading={busyAction === "ai-summary"} onClick={loadAiSummary}>
                AI recovery summary
              </Button>
              <Button variant="ghost" disabled={busy} onClick={() => loadAll()}>
                Refresh
              </Button>
            </div>
            {aiSummary ? <div className="ai-summary"><span className="badge">Summary · {aiSource}</span><Banner tone="info"><p>{aiSummary}</p></Banner></div> : null}
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
                      {d.is_demo ? (
                        <span className="badge badge-demo">Demo</span>
                      ) : null}
                    </header>
                    <div>
                      Remaining {d.remaining_portions} · Declines{" "}
                      {d.declined_invitations} · Pending {d.pending_invitations}
                    </div>
                    {d.needs_recovery ? (
                      <Button
                        disabled={busy && busyAction !== `recovery-${d.donation_id}`}
                        loading={busyAction === `recovery-${d.donation_id}`}
                        onClick={() => runRecovery(d.donation_id)}
                      >
                        Rematch now
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title="Recent donor feedback">
            {reviews.length === 0 ? <Empty>No donor reviews have been submitted yet.</Empty> : (
              <div className="list">
                {reviews.map((review) => (
                  <div key={review.id} className="list-item">
                    <header>
                      <strong>{review.donor_name} · {"★".repeat(review.rating)}{"☆".repeat(5 - review.rating)}</strong>
                      <span className="badge">Donation #{review.donation_id}</span>
                    </header>
                    <div className="muted">{review.food_name ?? "Donation"} · reviewed by {review.recipient_name ?? "recipient"}</div>
                    {review.feedback ? <p>{review.feedback}</p> : <p className="muted">No written feedback.</p>}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
