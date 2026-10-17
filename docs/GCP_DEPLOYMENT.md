# Google Cloud Deployment Guide

Target stack: **Cloud Run** (API + donor/recipient/admin UIs) · **Cloud SQL PostgreSQL** · **Secret Manager** · **Vertex AI** (optional).

Default region: **asia-south1**. Use your existing project ID from `gcloud config get-value project`.

Auth for the cup demo: **`DEMO_MODE=true`** with `X-Demo-Role` headers from the Vite apps (`VITE_AUTH_MODE=demo`). No Firebase.

---

## 0. Production rules (enforced at API startup)

When `ENVIRONMENT=production` the API **refuses to start** unless:

| Variable | Requirement |
|----------|-------------|
| `DEMO_MODE` | `true` (demo role headers) |
| `DATABASE_URL` | PostgreSQL (not SQLite) |
| `CORS_ORIGINS` | Exact `https://` Cloud Run UI URLs **or `*` for first boot (caution)** |
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

Inspect existing services before overwriting:

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

Store `DATABASE_URL` in Secret Manager (never as plain env in git):

```bash
PROJECT=$(gcloud config get-value project)
CONN="${PROJECT}:asia-south1:foodbridge-pg"
printf 'postgresql+psycopg2://foodbridge:PASSWORD@/foodbridge?host=/cloudsql/%s' "$CONN" | \
  gcloud secrets create foodbridge-database-url --data-file=-
# To rotate later:
# printf '...' | gcloud secrets versions add foodbridge-database-url --data-file=-
```

---

## 3. Deploy API (Cloud Run)

```bash
chmod +x deploy/*.sh

# First boot — CORS can be * until UI URLs exist; create tables once
export CORS_ORIGINS="*"
export CLOUDSQL_INSTANCE="$(gcloud config get-value project):asia-south1:foodbridge-pg"

AUTO_CREATE_TABLES=true ./deploy/deploy.sh \
  --cors-origins "$CORS_ORIGINS" \
  --cloudsql "$CLOUDSQL_INSTANCE"

# Steady state (after you know UI URLs — see step 4)
AUTO_CREATE_TABLES=false ./deploy/deploy.sh \
  --cors-origins "$CORS_ORIGINS" \
  --cloudsql "$CLOUDSQL_INSTANCE"
```

The script mounts secret `foodbridge-database-url` → `DATABASE_URL`, sets `DEMO_MODE=true`, and attaches Cloud SQL.

---

## 4. Deploy frontends (Cloud Run)

```bash
API_URL=$(gcloud run services describe foodbridge-rescueflow \
  --region=asia-south1 --format='value(status.url)')

export VITE_API_URL="$API_URL"
./deploy/deploy_frontend.sh
```

This builds three nginx images and deploys:

| Service | Role |
|---------|------|
| `foodbridge-donor-ui` | Donor app |
| `foodbridge-recipient-ui` | Recipient app |
| `foodbridge-admin-ui` | Admin app |

The script prints the three UI URLs. Lock API CORS to them:

```bash
# Use the CORS_ORIGINS line printed by deploy_frontend.sh, or:
gcloud run services update foodbridge-rescueflow \
  --region=asia-south1 \
  --update-env-vars="CORS_ORIGINS=https://foodbridge-donor-ui-XXXX.a.run.app,https://foodbridge-recipient-ui-XXXX.a.run.app,https://foodbridge-admin-ui-XXXX.a.run.app"
```

Or copy from `frontend/*/.env.production.example` and build manually.

---

## 5. Smoke test

```bash
URL=$(gcloud run services describe foodbridge-rescueflow --region=asia-south1 --format='value(status.url)')
./deploy/smoke_test.sh "$URL"
# Expect health 200; with DEMO_MODE=true, seed works with X-Demo-Role: admin
```

---

## 6. IAM (least privilege)

Runtime compute SA typically needs:

- `roles/secretmanager.secretAccessor` on `foodbridge-database-url`
- `roles/cloudsql.client`
- `roles/aiplatform.user` (if Gemini enabled)

Do **not** grant Owner/Editor to make deploy work.

---

## 7. Cost & cleanup

Charges while idle: Cloud SQL instance (largest), Artifact Registry, Vertex usage.

```bash
gcloud run services delete foodbridge-rescueflow --region=asia-south1
gcloud run services delete foodbridge-donor-ui --region=asia-south1
gcloud run services delete foodbridge-recipient-ui --region=asia-south1
gcloud run services delete foodbridge-admin-ui --region=asia-south1
# gcloud sql instances delete foodbridge-pg   # destructive
```

---

## Local vs Cloud Run auth

| Mode | Frontend | Backend |
|------|----------|---------|
| Local / Cloud Shell | `VITE_AUTH_MODE` unset / demo | `DEMO_MODE=true`, localhost CORS / Vite proxy |
| Cloud Run | `VITE_AUTH_MODE=demo` + `X-Demo-Role` | `DEMO_MODE=true`, `CORS_ORIGINS=https://…-ui-….a.run.app` |

Prefer locking CORS to the three UI Cloud Run origins rather than leaving `*`.
