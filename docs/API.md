# API Reference — `/api/v1`

Auth: demo headers `X-Demo-Role`, `X-Demo-User-Id`, optional `X-Demo-Recipient-Id` when `DEMO_MODE=true`.

Errors: FastAPI detail string/object with HTTP 4xx/5xx.

## Health

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | none | Liveness |
| GET | `/api/v1/health` | none | Same payload |

## Demo

| Method | Path | Role | Notes |
|--------|------|------|-------|
| POST | `/api/v1/demo/seed?force=false` | admin | Blocked when `DEMO_MODE=false` |

## Donations

### POST `/api/v1/donations` — donor|admin

Request:
```json
{
  "donor_name": "Harbor Bistro",
  "category": "vegetarian",
  "food_name": "Veg thali",
  "total_portions": 120,
  "pickup_deadline": "2026-10-17T14:00:00Z",
  "pickup_address": "12 Market St",
  "notes": "optional",
  "is_demo": true
}
```

Rules: timezone-aware future deadline; `total_portions > 0`. Creates invitations.

### GET `/api/v1/donations` — any authenticated
### GET `/api/v1/donations/{id}` — any authenticated (donor scoped by org when set)
### GET `/api/v1/donations/{id}/matches` — ranked invitations with scores/reasons

## Recipients

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/recipients` | admin\|donor |
| GET | `/api/v1/recipients/me/invitations` | recipient\|admin |
| GET | `/api/v1/recipients/{id}` | authenticated |

## Invitations

| Method | Path | Role | Business rule |
|--------|------|------|---------------|
| GET | `/api/v1/invitations/{id}` | recipient\|admin\|donor | |
| POST | `/api/v1/invitations/{id}/accept` | recipient\|admin | Allocates min(suggested, remaining, capacity); 409 if stale/zero |
| POST | `/api/v1/invitations/{id}/decline` | recipient\|admin | No stock change; rematch |

## Allocations

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/allocations` | authenticated |
| PATCH | `/api/v1/allocations/{id}/pickup` | recipient\|admin\|donor |

Body: `{ "pickup_status": "pending|confirmed|completed|failed" }`

## Admin

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/admin/dashboard` | admin |
| GET | `/api/v1/admin/recovery` | admin |
| POST | `/api/v1/admin/recovery/{donation_id}` | admin |
| GET | `/api/v1/admin/audit-events` | admin |

## AI

| Method | Path | Role | Notes |
|--------|------|------|-------|
| POST | `/api/v1/ai/explain-match` | donor\|admin | Body `{ "donation_id": 1 }` — Gemini or fallback |
| GET | `/api/v1/ai/recovery-summary` | admin | |

## Matches

| Method | Path | Role |
|--------|------|------|
| POST | `/api/v1/matches/{donation_id}/refresh` | donor\|admin |

## Stale offer policy

On accept, fulfill `min(suggested, remaining, capacity)`. If result is 0 → HTTP 409 asking client to refresh. Partial accepts leave other pending invites active and rebalance their suggested quantities.
