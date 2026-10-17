import { FormEvent, useEffect, useMemo, useState } from "react";
import { createApiClient, ApiError } from "@foodbridge/shared/api/client";
import { Banner, Button, Card, Empty, Shell, Stat } from "@foodbridge/shared/components/ui";
import type {
  Donation,
  ExplainMatchResponse,
  MatchOffer,
} from "@foodbridge/shared/types";

function defaultDeadline(): string {
  const d = new Date(Date.now() + 2 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function App() {
  const api = useMemo(() => createApiClient({ role: "donor" }), []);
  const [donations, setDonations] = useState<Donation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [matches, setMatches] = useState<MatchOffer[]>([]);
  const [explanation, setExplanation] = useState<ExplainMatchResponse | null>(null);
  const [message, setMessage] = useState<{ tone: "success" | "error" | "info"; text: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const [form, setForm] = useState({
    donor_name: "Harbor Bistro",
    category: "vegetarian",
    food_name: "Vegetarian thali",
    total_portions: 120,
    pickup_deadline: defaultDeadline(),
    pickup_address: "12 Market Street (demo)",
    notes: "Synthetic demo donation",
  });

  async function refreshDonations() {
    const rows = await api.get<Donation[]>("/api/v1/donations");
    setDonations(rows);
    if (rows.length && selectedId == null) setSelectedId(rows[0].id);
  }

  async function loadMatches(id: number) {
    const rows = await api.get<MatchOffer[]>(`/api/v1/donations/${id}/matches`);
    setMatches(rows);
  }

  useEffect(() => {
    refreshDonations().catch((e) =>
      setMessage({ tone: "error", text: e instanceof Error ? e.message : "Failed to load" })
    );
  }, []);

  useEffect(() => {
    if (selectedId == null) return;
    loadMatches(selectedId).catch(() => setMatches([]));
  }, [selectedId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.total_portions <= 0) {
      setMessage({ tone: "error", text: "Portion quantity must be greater than zero." });
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const deadline = new Date(form.pickup_deadline);
      const created = await api.post<Donation>("/api/v1/donations", {
        ...form,
        pickup_deadline: deadline.toISOString(),
        is_demo: true,
      });
      setMessage({
        tone: "success",
        text: `Donation #${created.id} created with ${created.invitations_created ?? 0} ranked offers (demo).`,
      });
      setSelectedId(created.id);
      await refreshDonations();
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Could not create donation",
      });
    } finally {
      setLoading(false);
    }
  }

  async function explain() {
    if (selectedId == null) return;
    setLoading(true);
    try {
      const result = await api.post<ExplainMatchResponse>("/api/v1/ai/explain-match", {
        donation_id: selectedId,
      });
      setExplanation(result);
    } catch (err) {
      setMessage({
        tone: "error",
        text: err instanceof ApiError ? err.message : "Explanation unavailable",
      });
    } finally {
      setLoading(false);
    }
  }

  const selected = donations.find((d) => d.id === selectedId) ?? null;

  return (
    <Shell
      title="Donor workspace"
      subtitle="Publish surplus food, review ranked recovery offers, track remaining portions."
      role="Donor"
    >
      {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}

      <div className="grid-2">
        <Card title="Create surplus donation" tone="accent">
          <form onSubmit={onSubmit}>
            <label>
              Business name
              <input
                value={form.donor_name}
                onChange={(e) => setForm({ ...form, donor_name: e.target.value })}
                required
              />
            </label>
            <label>
              Food name
              <input
                value={form.food_name}
                onChange={(e) => setForm({ ...form, food_name: e.target.value })}
                required
              />
            </label>
            <label>
              Category
              <select
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="mixed">Mixed</option>
              </select>
            </label>
            <label>
              Portions
              <input
                type="number"
                min={1}
                value={form.total_portions}
                onChange={(e) =>
                  setForm({ ...form, total_portions: Number(e.target.value) })
                }
                required
              />
            </label>
            <label>
              Pickup deadline (local)
              <input
                type="datetime-local"
                value={form.pickup_deadline}
                onChange={(e) => setForm({ ...form, pickup_deadline: e.target.value })}
                required
              />
            </label>
            <label>
              Pickup address
              <input
                value={form.pickup_address}
                onChange={(e) => setForm({ ...form, pickup_address: e.target.value })}
              />
            </label>
            <label>
              Notes
              <textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </label>
            <Button type="submit" disabled={loading}>
              {loading ? "Saving…" : "Publish & match"}
            </Button>
          </form>
        </Card>

        <Card title="Your donations">
          {donations.length === 0 ? (
            <Empty>No donations yet. Create one to start recovery matching.</Empty>
          ) : (
            <div className="list">
              {donations.map((d) => (
                <button
                  key={d.id}
                  className="list-item"
                  style={{ textAlign: "left", cursor: "pointer" }}
                  onClick={() => setSelectedId(d.id)}
                >
                  <header>
                    <strong>
                      #{d.id} · {d.food_name}
                    </strong>
                    <span className="badge">{d.status}</span>
                  </header>
                  <div>
                    {d.remaining_portions}/{d.total_portions} portions remaining
                  </div>
                  {d.is_demo ? <span className="badge badge-demo">Synthetic demo</span> : null}
                </button>
              ))}
            </div>
          )}
        </Card>
      </div>

      {selected ? (
        <>
          <Card title={`Donation #${selected.id} status`}>
            <div className="stats">
              <Stat label="Remaining" value={selected.remaining_portions} />
              <Stat label="Total" value={selected.total_portions} />
              <Stat label="Status" value={selected.status} />
              <Stat
                label="Deadline"
                value={new Date(selected.pickup_deadline).toLocaleString()}
              />
            </div>
          </Card>

          <Card title="Ranked recipient offers">
            <div className="row-actions" style={{ marginBottom: "0.75rem" }}>
              <Button variant="secondary" onClick={() => loadMatches(selected.id)} disabled={loading}>
                Refresh matches
              </Button>
              <Button variant="ghost" onClick={explain} disabled={loading}>
                AI explanation
              </Button>
            </div>
            {matches.length === 0 ? (
              <Empty>No offers yet for this donation.</Empty>
            ) : (
              <div className="list">
                {matches.map((m) => (
                  <div key={m.invitation_id} className="list-item">
                    <header>
                      <strong>
                        Recipient #{m.recipient_id} · score {m.score}
                      </strong>
                      <span className="badge">{m.status}</span>
                    </header>
                    <div>Suggested offer: {m.suggested_portions} portions</div>
                    {m.reasons?.length ? (
                      <p className="muted">{m.reasons.join(" · ")}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {explanation ? (
            <Card title={`Recovery explanation (${explanation.source})`} tone="accent">
              <p>{explanation.summary}</p>
              {explanation.suggested_actions?.length ? (
                <ul>
                  {explanation.suggested_actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              ) : null}
            </Card>
          ) : null}
        </>
      ) : null}
    </Shell>
  );
}
