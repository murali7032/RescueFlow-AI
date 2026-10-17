import { useEffect, useMemo, useState } from "react";
import { ApiError, createApiClient } from "@foodbridge/shared/api/client";
import { Banner, Button, Card, Empty, Shell, Stat } from "@foodbridge/shared/components/ui";
import type { Allocation, Invitation } from "@foodbridge/shared/types";

interface RecipientOption {
  id: number;
  name: string;
  available_capacity: number;
}

export default function App() {
  const [recipientId, setRecipientId] = useState<number | null>(null);
  const [recipients, setRecipients] = useState<RecipientOption[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [allocations, setAllocations] = useState<Allocation[]>([]);
  const [message, setMessage] = useState<{ tone: "success" | "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const api = useMemo(
    () => createApiClient({ role: "recipient", recipientId }),
    [recipientId]
  );
  const adminApi = useMemo(() => createApiClient({ role: "admin" }), []);

  useEffect(() => {
    adminApi
      .get<RecipientOption[]>("/api/v1/recipients")
      .then((rows) => {
        setRecipients(rows);
        if (rows.length && recipientId == null) setRecipientId(rows[0].id);
      })
      .catch((e) =>
        setMessage({ tone: "error", text: e instanceof Error ? e.message : "Load failed" })
      );
  }, []);

  async function refresh() {
    if (recipientId == null) return;
    const [inv, alloc] = await Promise.all([
      api.get<Invitation[]>(`/api/v1/recipients/me/invitations?recipient_id=${recipientId}`),
      api.get<Allocation[]>(`/api/v1/allocations?recipient_id=${recipientId}`),
    ]);
    setInvitations(inv);
    setAllocations(alloc);
  }

  useEffect(() => {
    refresh().catch((e) =>
      setMessage({ tone: "error", text: e instanceof Error ? e.message : "Refresh failed" })
    );
  }, [recipientId]);

  async function accept(id: number) {
    setBusy(true);
    setMessage(null);
    try {
      const result = await api.post<{ portions: number; pickup_status: string }>(
        `/api/v1/invitations/${id}/accept`
      );
      setMessage({
        tone: "success",
        text: `Accepted ${result.portions} portions. Pickup status: ${result.pickup_status}.`,
      });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Accept failed",
      });
    } finally {
      setBusy(false);
    }
  }

  async function decline(id: number) {
    setBusy(true);
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
    }
  }

  async function confirmPickup(allocationId: number) {
    setBusy(true);
    try {
      await api.patch(`/api/v1/allocations/${allocationId}/pickup`, {
        pickup_status: "confirmed",
      });
      setMessage({ tone: "success", text: "Pickup confirmed (still separate from meals served)." });
      await refresh();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Pickup update failed",
      });
    } finally {
      setBusy(false);
    }
  }

  const pending = invitations.filter((i) => i.status === "pending");
  const selected = recipients.find((r) => r.id === recipientId);

  return (
    <Shell
      title="Recipient inbox"
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
    >
      {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}

      <Card title="Capacity snapshot">
        <div className="stats">
          <Stat label="Kitchen" value={selected?.name ?? "—"} />
          <Stat label="Available capacity" value={selected?.available_capacity ?? "—"} />
          <Stat label="Pending offers" value={pending.length} />
          <Stat label="Allocations" value={allocations.length} />
        </div>
      </Card>

      <Card title="Invitations" tone="accent">
        {pending.length === 0 ? (
          <Empty>No pending invitations for this kitchen.</Empty>
        ) : (
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
                      Deadline {new Date(inv.donation.pickup_deadline).toLocaleString()} ·{" "}
                      {inv.donation.pickup_address}
                    </div>
                    <div className="muted">
                      Donation remaining: {inv.donation.remaining_portions} portions
                    </div>
                  </>
                ) : null}
                {inv.reasons?.length ? (
                  <p className="muted">{inv.reasons.join(" · ")}</p>
                ) : null}
                <div className="row-actions">
                  <Button disabled={busy} onClick={() => accept(inv.id)}>
                    Accept
                  </Button>
                  <Button variant="danger" disabled={busy} onClick={() => decline(inv.id)}>
                    Decline
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Allocations & pickup">
        {allocations.length === 0 ? (
          <Empty>No allocations yet. Accepting an offer reserves portions here.</Empty>
        ) : (
          <div className="list">
            {allocations.map((a) => (
              <div key={a.id} className="list-item">
                <header>
                  <strong>
                    Allocation #{a.id} · {a.portions} portions
                  </strong>
                  <span className="badge">{a.pickup_status}</span>
                </header>
                <div className="muted">Donation #{a.donation_id}</div>
                {a.pickup_status === "pending" ? (
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => confirmPickup(a.id)}
                  >
                    Confirm pickup
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </Card>
    </Shell>
  );
}
