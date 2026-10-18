# Architecture — RescueFlow AI by FoodBridge

## System overview

```mermaid
flowchart LR
  WebUI[Unified Vite React App] --> API[FastAPI Cloud Run]
  WebUI --> Donor[Donor Workspace]
  WebUI --> Recipient[Recipient Workspace]
  WebUI --> Admin[Admin Dashboard]
  API --> DB[(PostgreSQL / SQLite)]
  API --> Match[Deterministic Matching]
  API --> Alloc[Transactional Allocations]
  API --> Recovery[Recovery Rematch]
  API --> Agent[Gemini Explanation Agent]
  Agent -->Vertex[Vertex AI Gemini]
  Scheduler[Cloud Scheduler] -->|every minute| TimeoutJob[Cloud Run timeout job]
  TimeoutJob --> DB
  TimeoutJob --> Match
```

## Request flows

1. **Create donation** → validate deadline/quantity → persist `Donation` → `create_invitations` ranks eligible recipients → audit event.
2. **Decline invitation** → mark declined (no stock change) → rematch remaining stock → audit.
3. **Timeout** → scheduled Cloud Run Job locks due invitation/donation rows → expire timed-out offers → if pickup deadline is still open, exclude that recipient and rematch; otherwise expire pending offers and donation.
4. **Accept invitation** → row locks (Postgres) → reject expired offers → allocate `min(suggested, remaining, capacity)` → update donation status → cancel pending only if remaining=0, else rebalance offers → allocation with `pickup_status=pending`.
5. **Confirm pickup** → separate state transition on allocation; does not change donation ledger.

## State machines

### Donation
`open` → `partially_allocated` → `allocated`  
also: `expired`, `cancelled`

### Invitation
`pending` → `accepted` | `declined` | `cancelled` | `expired`

New invitations expire at the earlier of `created_at + INVITATION_RESPONSE_TIMEOUT_MINUTES` (default 15) and the donation pickup deadline. Expired recipients are not automatically re-invited.

### Pickup (on Allocation)
`pending` → `confirmed` → `completed` (or `failed`)

## Matching & recovery

Hard filters before scoring: donation open/partial, remaining > 0, recipient active, category compatible, earliest pickup within deadline, not previously accepted/declined/cancelled (no auto re-invite).

Score weights (configurable): deadline 35%, capacity 30%, distance 20%, preference 15%. Distance is **synthetic demo data**, not live traffic.

Recovery = rematch remaining stock after declines/timeouts without cancelling valid pending offers after partial accepts. Cloud Scheduler runs the one-shot timeout worker every minute; each donation is processed in its own transaction. The worker uses row locks and can safely be retried.

## Concurrency

Accept, decline, manual recovery, and the timeout worker lock the donation before its invitations (then recipient for acceptance) to maintain a consistent lock order. Verified concurrency tests require PostgreSQL (`CONCURRENCY_DATABASE_URL`). SQLite is for local/demo only.

## Security boundaries

- Identity from demo headers (`X-Demo-Role`) on the unified web app (page role per workspace; optional DEV-only override).
- Roles: donor, recipient, admin. Recipients cannot accept another kitchen’s invites.
- AI tools are read-only; the model cannot allocate or write DB rows.

## AI responsibilities

Gemini (Vertex) explains rankings and recovery. If credentials/timeouts fail, deterministic fallback summaries are returned. Core workflows never depend on the model.
