# RescueFlow AI by FoodBridge

AI-assisted surplus food recovery and allocation for the AI Builder Cup 2026.

**Differentiator:** manage the recovery lifecycle **after** a match fails—declines, partial capacity, rematching—without over-allocating portions. Pickup completion is tracked separately from allocation.

## Features

- Unified web app: Dashboard, Donor Workspace, Recipient Workspace, Admin Dashboard
- Donor donation publish + ranked recipient offers with explainable scores
- Recipient accept/decline with rematch recovery
- Transaction-minded allocations (Postgres row locks for concurrency)
- Admin dashboard with live metrics, recovery queue, audit trail
- Gemini explanations via Vertex AI with deterministic fallback
- Demo mode with eleven synthetic recipient organizations across multiple capacities and food categories (Kitchen D infeasible by deadline)

## Architecture

One FastAPI backend, one Vite + React + TypeScript frontend (shared UI/API client under `frontend/shared`). Both deploy to **Cloud Run**. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository structure

```text
frontend/{src,shared}          # unified SPA
backend/app/{api,services,agent,db,workers}
backend/tests
deploy/{deploy.sh,deploy_frontend.sh,smoke_test.sh}
docs/*
```

## Prerequisites

- Python 3.11+
- Node 20+
- Optional: Docker, gcloud, PostgreSQL

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

## Frontend (unified)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Routes: `/` Dashboard · `/donor` · `/recipient` · `/admin`

Leave `VITE_API_URL` empty for Vite proxy to `:8000`, or set `VITE_API_URL=http://localhost:8000`.

A **dev-only** demo role switcher appears in the sidebar during `npm run dev`. It is disabled in production builds.

## Demo seed

From Dashboard / Admin (**Seed demo**) or:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed -H "X-Demo-Role: admin"
```

## Tests

```bash
cd backend && pytest -q
cd frontend && npm test && npm run build
```

## Deployment

- [docs/GCP_DEPLOYMENT.md](docs/GCP_DEPLOYMENT.md)
- Backend: `./deploy/deploy.sh` → Cloud Run `foodbridge-rescueflow`
- Frontend: `./deploy/deploy_frontend.sh` → Cloud Run `foodbridge-ui`

Documented URLs after deploy:

| Service | Cloud Run name | Env |
|---------|----------------|-----|
| Backend API | `foodbridge-rescueflow` | set as `VITE_API_URL` when building UI |
| Unified UI | `foodbridge-ui` | set as `CORS_ORIGINS` on the API |

## Environment

See `backend/.env.example`, `frontend/.env.example`, and `deploy/env.production.example`.

Never commit secrets. Do not claim Cloud Run deployment succeeded until health/smoke checks pass against the live URLs.
