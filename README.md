# RescueFlow AI by FoodBridge

AI-assisted surplus food recovery and allocation for the AI Builder Cup 2026.

**Differentiator:** manage the recovery lifecycle **after** a match fails—declines, partial capacity, rematching—without over-allocating portions. Pickup completion is tracked separately from allocation.

## Features

- Donor donation publish + ranked recipient offers with explainable scores
- Recipient accept/decline with rematch recovery
- Transaction-minded allocations (Postgres row locks for concurrency)
- Admin dashboard with live metrics, recovery queue, audit trail
- Gemini explanations via Vertex AI with deterministic fallback
- Demo mode with synthetic kitchens A–D (D infeasible by deadline)

## Architecture

One FastAPI backend, three Vite + React + TypeScript frontends, shared UI/API client. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository structure

```text
frontend/{donor,recipient,admin,shared}
backend/app/{api,services,agent,db,workers}
backend/tests
deploy/{deploy.sh,smoke_test.sh}
docs/*
```

## Prerequisites

- Python 3.11+
- Node 20+
- Optional: Docker, gcloud, PostgreSQL, Firebase

## Local backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # or cp
set PYTHONPATH=%CD%
uvicorn app.main:app --reload --port 8000
```

Health: http://localhost:8000/health · Docs: http://localhost:8000/docs

With `DEMO_MODE=true` (default in development), send `X-Demo-Role: admin|donor|recipient`.

## Frontend

```bash
cd frontend/donor && npm install && npm run dev      # :5173
cd frontend/recipient && npm install && npm run dev  # :5174
cd frontend/admin && npm install && npm run dev      # :5175
```

Set `VITE_API_URL=http://localhost:8000` if needed.

## Demo seed

From Admin UI (**Seed demo** / **Reset & reseed**) or:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed -H "X-Demo-Role: admin"
```

## Tests

```bash
cd backend && pytest -q
cd frontend/donor && npm test && npm run build
```

Details: [docs/TESTING.md](docs/TESTING.md)

## Deployment

- [docs/GCP_DEPLOYMENT.md](docs/GCP_DEPLOYMENT.md)
- `./deploy/deploy.sh` · `./deploy/smoke_test.sh`

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/API.md](docs/API.md) | Endpoints & business rules |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | 3–4 minute pitch |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common failures |

## Environment

See `backend/.env.example`. Production must set `ENVIRONMENT=production`, `DEMO_MODE=false`, and a Postgres `DATABASE_URL`. Never commit secrets.
