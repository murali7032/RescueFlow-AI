# Google Cloud Deployment Guide

Target stack: **Cloud Run** (API + unified UI) · **Cloud SQL PostgreSQL** · **Secret Manager** · **Vertex AI** (optional).

Default region: **asia-south1**. Use your existing project ID from `gcloud config get-value project`.

Auth for the cup demo: open demo headers (`X-Demo-Role`) from the Vite app. No Firebase.

**Services**

| Cloud Run service | Purpose |
|-------------------|---------|
| `foodbridge-rescueflow` | FastAPI backend |
| `foodbridge-ui` | Unified React frontend (Dashboard, Donor, Recipient, Admin) |

---

## 0. Production rules (enforced at API startup)

When `ENVIRONMENT=production` the API **refuses to start** unless:

| Variable | Requirement |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (not SQLite) |
| `CORS_ORIGINS` | Exact `https://` UI Cloud Run URL **or `*` for first boot (caution)** |
| `GOOGLE_CLOUD_PROJECT` | Set |

OpenAPI `/docs` is disabled in production.

---

## 1. Project & APIs

```bash
gcloud config get-value project
gcloud config set run/region asia-south1

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  aiplatform.googleapis.com
```

```bash
gcloud run services list --region=asia-south1
```

---

## 2. Cloud SQL

```bash
# Skip create if you already have an instance
gcloud sql instances create foodbridge-pg \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-south1

gcloud sql databases create foodbridge --instance=foodbridge-pg
gcloud sql users create foodbridge --instance=foodbridge-pg --password='GENERATE_STRONG_PASSWORD'
```

Store `DATABASE_URL` in Secret Manager:

```bash
PROJECT=$(gcloud config get-value project)
CONN="${PROJECT}:asia-south1:foodbridge-pg"
printf 'postgresql+psycopg2://foodbridge:PASSWORD@/foodbridge?host=/cloudsql/%s' "$CONN" | \
  gcloud secrets create foodbridge-database-url --data-file=-
```

---

## 3. Deploy API (Cloud Run)

```bash
chmod +x deploy/*.sh

export CORS_ORIGINS="*"
export CLOUDSQL_INSTANCE="$(gcloud config get-value project):asia-south1:foodbridge-pg"

AUTO_CREATE_TABLES=true ./deploy/deploy.sh \
  --cors-origins "$CORS_ORIGINS" \
  --cloudsql "$CLOUDSQL_INSTANCE"
```

---

## 4. Deploy unified frontend (Cloud Run)

```bash
API_URL=$(gcloud run services describe foodbridge-rescueflow \
  --region=asia-south1 --format='value(status.url)')

export VITE_API_URL="$API_URL"
./deploy/deploy_frontend.sh
```

Deploys service **`foodbridge-ui`**. The script prints:

- Frontend URL → open this in the browser
- Backend URL → already baked into the bundle as `VITE_API_URL`

Lock API CORS to the single UI origin:

```bash
UI_URL=$(gcloud run services describe foodbridge-ui \
  --region=asia-south1 --format='value(status.url)')

gcloud run services update foodbridge-rescueflow \
  --region=asia-south1 \
  --update-env-vars="CORS_ORIGINS=${UI_URL}"
```

Local / manual build: copy `frontend/.env.production.example` → `frontend/.env.production`, set `VITE_API_URL`, then `npm run build`.

---

## 5. Smoke test

```bash
URL=$(gcloud run services describe foodbridge-rescueflow --region=asia-south1 --format='value(status.url)')
./deploy/smoke_test.sh "$URL"
```

Do **not** claim Cloud Run deployment succeeded until `gcloud run services describe` returns ready URLs and smoke/health checks pass.

---

## 6. IAM (least privilege)

Runtime compute SA typically needs:

- `roles/secretmanager.secretAccessor` on `foodbridge-database-url`
- `roles/cloudsql.client`
- `roles/aiplatform.user` (if Gemini enabled)

---

## 7. Cost & cleanup

```bash
gcloud run services delete foodbridge-rescueflow --region=asia-south1
gcloud run services delete foodbridge-ui --region=asia-south1
# gcloud sql instances delete foodbridge-pg   # destructive
```

Optional: delete legacy `foodbridge-donor-ui` / `foodbridge-recipient-ui` / `foodbridge-admin-ui` if they still exist from earlier deploys.

---

## Local vs Cloud Run

| Mode | Frontend | Backend |
|------|----------|---------|
| Local | `cd frontend && npm run dev` (:5173), Vite proxy | `DEMO_MODE=true`, localhost CORS |
| Cloud Run | `foodbridge-ui` with `VITE_API_URL` | `CORS_ORIGINS=https://foodbridge-ui-….a.run.app` |

Dev-only demo role switcher appears in `npm run dev` only; it is stripped from production builds (`import.meta.env.DEV`).
