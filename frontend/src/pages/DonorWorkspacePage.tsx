import { FormEvent, useEffect, useState } from "react";
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
import type {
  Donation,
  ExplainMatchResponse,
  MatchOffer,
} from "@foodbridge/shared/types";
import { formatDateTime, formatMatchReason } from "@foodbridge/shared/format";
import { useApi } from "../hooks/useApi";

function defaultDeadline(): string {
  const d = new Date(Date.now() + 2 * 60 * 60 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function DonorWorkspacePage() {
  const api = useApi("donor");
  const [donations, setDonations] = useState<Donation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [matches, setMatches] = useState<MatchOffer[]>([]);
  const [explanation, setExplanation] = useState<ExplainMatchResponse | null>(null);
  const [message, setMessage] = useState<{
    tone: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);

  const [form, setForm] = useState({
    donor_name: "Harbor Bistro",
    donor_type: "restaurant" as "restaurant" | "business" | "individual",
    category: "vegetarian",
    food_name: "Vegetarian thali",
    total_portions: 120,
    pickup_deadline: defaultDeadline(),
    pickup_address: "12 Market Street (demo)",
    notes: "Synthetic demo donation",
  });

  async function refreshDonations() {
    setLoadingList(true);
    try {
      const rows = await api.get<Donation[]>("/api/v1/donations");
      setDonations(rows);
      if (rows.length && selectedId == null) setSelectedId(rows[0].id);
      setMessage(null);
    } catch (e) {
      setMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "Failed to load donations",
      });
    } finally {
      setLoadingList(false);
    }
  }

  async function loadMatches(id: number) {
    try {
      const rows = await api.get<MatchOffer[]>(`/api/v1/donations/${id}/matches`);
      setMatches(rows);
    } catch {
      setMatches([]);
    }
  }

  useEffect(() => {
    refreshDonations();
  }, []);

  useEffect(() => {
    if (selectedId == null) return;
    loadMatches(selectedId);
  }, [selectedId]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (form.total_portions <= 0) {
      setMessage({ tone: "error", text: "Portion quantity must be greater than zero." });
      return;
    }
    setBusy(true);
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
      setBusy(false);
    }
  }

  async function explain() {
    if (selectedId == null) return;
    setBusy(true);
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
      setBusy(false);
    }
  }

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setMessage({ tone: "error", text: "Location is not available in this browser." });
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setForm((current) => ({ ...current, pickup_address: `${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}` }));
        setMessage({ tone: "info", text: "Pickup coordinates added. You can edit the address before publishing." });
        setLocating(false);
      },
      () => {
        setMessage({ tone: "error", text: "Could not get your location. Allow location access or enter the address manually." });
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );
  }

  const selected = donations.find((d) => d.id === selectedId) ?? null;

  return (
    <div className="page">
      <PageHeader
        title="Donor workspace"
        subtitle="Publish surplus food, review ranked recovery offers, track remaining portions."
        role="Donor"
        actions={
          <label className="donor-type-select" style={{ margin: 0 }}>
            Donor type
            <select value={form.donor_type} onChange={(e) => setForm({ ...form, donor_type: e.target.value as typeof form.donor_type })}>
              <option value="restaurant">Restaurant</option>
              <option value="business">Company / business</option>
              <option value="individual">Individual donor</option>
            </select>
          </label>
        }
      />

      <div className="content">
        {message ? <Banner tone={message.tone}>{message.text}</Banner> : null}

        <div className="grid-2">
          <Card title="Create surplus donation" tone="accent">
            <form onSubmit={onSubmit}>
              <label>
                {form.donor_type === "individual" ? "Donor name" : form.donor_type === "business" ? "Company / business name" : "Restaurant name"}
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
                <div className="address-field">
                  <input value={form.pickup_address} onChange={(e) => setForm({ ...form, pickup_address: e.target.value })} />
                  <Button variant="secondary" className="address-locate" onClick={useCurrentLocation} loading={locating}>Use my location</Button>
                </div>
              </label>
              <label>
                Notes
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </label>
              <Button type="submit" loading={busy}>
                Publish & match
              </Button>
            </form>
          </Card>

          <Card title="Your donations">
            {loadingList ? <Loading>Loading donations…</Loading> : null}
            {!loadingList && donations.length === 0 ? (
              <Empty>No donations yet. Create one to start recovery matching.</Empty>
            ) : null}
            {!loadingList && donations.length > 0 ? (
              <div className="list">
                {donations.map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    className="list-item"
                    style={{ textAlign: "left", cursor: "pointer", width: "100%" }}
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
                    {d.is_demo ? (
                      <span className="badge badge-demo">Synthetic demo</span>
                    ) : null}
                  </button>
                ))}
              </div>
            ) : null}
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
                  value={formatDateTime(selected.pickup_deadline)}
                />
                <Stat label="Donor trust score" value={`${selected.donor_score ?? 50}/100`} hint={`${selected.donor_review_count ?? 0} recipient reviews`} />
              </div>
            </Card>

            <Card title="Ranked recipient offers">
              <div className="row-actions" style={{ marginBottom: "0.75rem" }}>
                <Button
                  variant="secondary"
                  onClick={() => loadMatches(selected.id)}
                  disabled={busy}
                >
                  Refresh matches
                </Button>
                <Button variant="ghost" onClick={explain} loading={busy}>
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
                          {m.recipient_name ?? `Recipient #${m.recipient_id}`} · match score {m.score}/100
                        </strong>
                        <span className="badge">{m.status}</span>
                      </header>
                      <div>Suggested offer: {m.suggested_portions} portions</div>
                      {m.reasons?.length ? (
                        <p className="muted">{m.reasons.map(formatMatchReason).join(" · ")}</p>
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
      </div>
    </div>
  );
}
