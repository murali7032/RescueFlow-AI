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
import type { Allocation, Invitation } from "@foodbridge/shared/types";
import { useApi } from "../hooks/useApi";
import { useDemoRole } from "../context/DemoRoleContext";
import { formatDateTime, formatMatchReason } from "@foodbridge/shared/format";

interface RecipientOption {
  id: number;
  name: string;
  available_capacity: number;
}

export default function RecipientWorkspacePage() {
  const { recipientId, setRecipientId } = useDemoRole();
  const [recipients, setRecipients] = useState<RecipientOption[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState<Allocation | null>(null);
  const [reviewRating, setReviewRating] = useState(5);
  const [reviewFeedback, setReviewFeedback] = useState("");

  const api = useApi("recipient", recipientId);
  const adminApi = useApi("admin");

  useEffect(() => {
    adminApi
      .get<RecipientOption[]>("/api/v1/recipients")
      .then((rows) => {
        setRecipients(rows);
        if (rows.length && recipientId == null) setRecipientId(rows[0].id);
      })
      .catch((e) =>
        setMessage({
          tone: "error",
          text: e instanceof Error ? e.message : "Load failed",
        })
      );
  }, []);

  async function refresh() {
    if (recipientId == null) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [inv, alloc] = await Promise.all([
        api.get<Invitation[]>(
          `/api/v1/recipients/me/invitations?recipient_id=${recipientId}`
        ),
        api.get<Allocation[]>(`/api/v1/allocations?recipient_id=${recipientId}`),
      ]);
      setInvitations(inv);
      setAllocations(alloc);
    } catch (e) {
      setMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "Refresh failed",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [recipientId]);

  async function accept(id: number) {
    setBusy(true);
    setBusyAction(`accept-${id}`);
    setMessage(null);
    try {
      const result = await api.post<{ portions: number; pickup_status: string }>(
        `/api/v1/invitations/${id}/accept`
      );
      setMessage({
        tone: "success",
        text: `Accepted ${result.portions} portions (allocated). Pickup status: ${result.pickup_status} — not yet completed.`,
      });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Accept failed",
      });
    } finally {
      setBusy(false);
      setBusyAction(null);
    }
  }

  async function decline(id: number) {
    setBusy(true);
    setBusyAction(`decline-${id}`);
    setMessage(null);
    try {
      const result = await api.post<{ status: string; new_invitations_created: number }>(
        `/api/v1/invitations/${id}/decline`
      );
      setMessage({
        tone: "info",
        text: `Declined. Stock unchanged. Recovery rematch created ${result.new_invitations_created} offer(s).`,
      });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Decline failed",
      });
    } finally {
      setBusy(false);
      setBusyAction(null);
    }
  }

  async function confirmPickup(allocationId: number) {
    setBusy(true);
    setBusyAction(`pickup-${allocationId}`);
    try {
      await api.patch(`/api/v1/allocations/${allocationId}/pickup`, {
        pickup_status: "confirmed",
      });
      setMessage({
        tone: "success",
        text: "Pickup confirmed (still separate from meals served / completed).",
      });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Pickup update failed",
      });
    } finally {
      setBusy(false);
      setBusyAction(null);
    }
  }

  async function submitReview() {
    if (!reviewing) return;
    setBusy(true);
    setBusyAction(`review-${reviewing.id}`);
    try {
      const result = await api.post<{ donor_score: number; restricted: boolean }>(
        `/api/v1/allocations/${reviewing.id}/review`,
        { rating: reviewRating, feedback: reviewFeedback },
      );
      setMessage({ tone: "success", text: `Review saved. Donor trust score: ${result.donor_score}/100.${result.restricted ? " The donor has been paused for support review." : ""}` });
      setReviewing(null);
      setReviewFeedback("");
      await refresh();
    } catch (err) {
      setMessage({ tone: "error", text: err instanceof ApiError ? err.message : "Could not save review" });
    } finally {
      setBusy(false);
      setBusyAction(null);
    }
  }

  const pending = invitations.filter((i) => i.status === "pending");
  const selected = recipients.find((r) => r.id === recipientId);
  const allocatedPortions = allocations.reduce((s, a) => s + a.portions, 0);
  const completedPortions = allocations
    .filter((a) => a.pickup_status === "completed")
    .reduce((s, a) => s + a.portions, 0);

  return (
    <div className="page">
      <PageHeader
        title="Recipient workspace"
        subtitle="Review offers, accept or decline, and confirm pickup separately from allocation."
        role="Recipient"
        actions={
          <label style={{ margin: 0, minWidth: 220 }}>
            Act as kitchen
            <select
              value={recipientId ?? ""}
              onChange={(e) => setRecipientId(Number(e.target.value))}
            >
              {recipients.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} (cap {r.available_capacity})
                </option>
              ))}
            </select>
          </label>
        }
      />

      <div className="content">
        {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}

        <Card title="Capacity snapshot">
          <div className="stats">
            <Stat label="Kitchen" value={selected?.name ?? "—"} />
            <Stat label="Available capacity" value={selected?.available_capacity ?? "—"} hint="Additional portions this kitchen can accept now" />
            <Stat label="Pending offers" value={pending.length} />
            <Stat
              label="Allocated portions"
              value={allocatedPortions}
              hint="Reserved stock"
            />
            <Stat
              label="Pickup completed"
              value={completedPortions}
              hint="Meals handed off"
            />
          </div>
        </Card>

        <Card title="Invitations" tone="accent">
          {loading ? <Loading>Loading invitations…</Loading> : null}
          {!loading && pending.length === 0 ? (
            <Empty>No pending invitations for this kitchen.</Empty>
          ) : null}
          {!loading && pending.length > 0 ? (
            <div className="list">
              {pending.map((inv) => (
                <div key={inv.id} className="list-item">
                  <header>
                    <strong>
                      Offer #{inv.id} · {inv.suggested_portions} portions
                    </strong>
                    <span className="badge">score {inv.score}</span>
                  </header>
                  {inv.donation ? (
                    <>
                      <div>
                        From {inv.donation.donor_name} · {inv.donation.food_name} (
                        {inv.donation.category})
                      </div>
                      <div className="muted">
                        Pickup by {formatDateTime(inv.donation.pickup_deadline)} ·{" "}
                        {inv.donation.pickup_address}
                      </div>
                      <div className="muted">
                        Respond by {formatDateTime(inv.expires_at)}
                      </div>
                      <div className="muted">
                        Donation remaining: {inv.donation.remaining_portions} portions
                      </div>
                    </>
                  ) : null}
                  {inv.reasons?.length ? (
                    <p className="muted">{inv.reasons.map(formatMatchReason).join(" · ")}</p>
                  ) : null}
                  <div className="row-actions">
                    <Button disabled={busy && busyAction !== `accept-${inv.id}`} loading={busyAction === `accept-${inv.id}`} onClick={() => accept(inv.id)}>
                      Accept
                    </Button>
                    <Button
                      variant="danger"
                      disabled={busy && busyAction !== `decline-${inv.id}`}
                      loading={busyAction === `decline-${inv.id}`}
                      onClick={() => decline(inv.id)}
                    >
                      Decline
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </Card>

        <Card title="Allocations & pickup">
          {loading ? <Loading>Loading allocations…</Loading> : null}
          {!loading && allocations.length === 0 ? (
            <Empty>No allocations yet. Accepting an offer reserves portions here.</Empty>
          ) : null}
          {!loading && allocations.length > 0 ? (
            <div className="list">
              {allocations.map((a) => (
                <div key={a.id} className="list-item">
                  <header>
                    <strong>
                      Allocation #{a.id} · {a.portions} portions allocated
                    </strong>
                    <span className="badge">pickup: {a.pickup_status}</span>
                  </header>
                  <div className="muted">Donation #{a.donation_id}</div>
                  {a.pickup_status === "pending" ? (
                    <Button
                      variant="secondary"
                      disabled={busy && busyAction !== `pickup-${a.id}`}
                      loading={busyAction === `pickup-${a.id}`}
                      onClick={() => confirmPickup(a.id)}
                    >
                      Confirm pickup
                    </Button>
                  ) : null}
                  {a.pickup_status === "confirmed" || a.pickup_status === "completed" ? (
                    a.reviewed ? <span className="badge">Review submitted</span> : (
                      <Button variant="secondary" onClick={() => { setReviewing(a); setReviewRating(5); setReviewFeedback(""); }}>
                        Review donor
                      </Button>
                    )
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </Card>
      </div>
      {reviewing ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setReviewing(null); }}>
          <section className="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
            <h2 id="review-title">Review {reviewing.donor_name ?? "the donor"}</h2>
            <p className="muted">How was the food and pickup for {reviewing.food_name ?? "this donation"}?</p>
            <div className="review-stars" role="radiogroup" aria-label="Rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <button key={star} type="button" className={`review-star ${star <= reviewRating ? "selected" : ""}`} aria-label={`${star} star${star === 1 ? "" : "s"}`} aria-checked={reviewRating === star} role="radio" onClick={() => setReviewRating(star)}>★</button>
              ))}
            </div>
            <label>Feedback (optional)<textarea maxLength={2000} value={reviewFeedback} onChange={(e) => setReviewFeedback(e.target.value)} placeholder="Share what went well or what could improve." /></label>
            <div className="row-actions">
              <Button variant="ghost" onClick={() => setReviewing(null)} disabled={busy}>Cancel</Button>
              <Button onClick={submitReview} loading={busyAction === `review-${reviewing.id}`}>Submit review</Button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
