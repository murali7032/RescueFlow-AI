# Google Cloud Deployment Guide

Target stack: **Cloud Run** (API) · **Cloud SQL PostgreSQL** · **Secret Manager** · **Firebase Auth** · **Vertex AI** (optional).

Default region: **asia-south1**. Use your existing project ID from `gcloud config get-value project`.

---

## 0. Production rules (enforced at API startup)

When `ENVIRONMENT=production` the API **refuses to start** unless:

| Variable | Requirement |
|----------|-------------|
| `DEMO_MODE` | `false` |
| `DATABASE_URL` | PostgreSQL (not SQLite) |
| `CORS_ORIGINS` | Exact `https://` Cloud Run UI URLs **or `*` for all origins (caution)** |
| `FIREBASE_PROJECT_ID` | Set |
| `GOOGLE_CLOUD_PROJECT` | Set |

OpenAPI `/docs` is disabled in production. Demo seed endpoints return 403.

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
  aiplatform.googleapis.com \
  identitytoolkit.googleapis.com
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

## 3. Firebase Auth (no Hosting)

1. Firebase console → add/use project (can match GCP project).
2. Enable **Authentication** (Email/Password and/or Google).
3. Register three web apps (donor, recipient, admin) and copy the config into your frontend `.env.production` (`VITE_FIREBASE_*`).
4. (Optional) Set **custom claims** on users via the Admin SDK or a Cloud Function, e.g. `{ "role": "donor" }` or `{ "role": "recipient", "recipient_id": 1 }`.

```bash
cp .firebaserc.example .firebaserc
# edit default project id
npm i -g firebase-tools
firebase login
firebase target:apply hosting foodbridge-donor foodbridge-donor  # if using targets; sites in firebase.json work with --only hosting
```

---

## 4. Deploy API (Cloud Run)

```bash
chmod +x deploy/*.sh

# First boot only — create tables once, then redeploy with AUTO_CREATE_TABLES=false
export CORS_ORIGINS="https://foodbridge-donor.web.app,https://foodbridge-recipient.web.app,https://foodbridge-admin.web.app"
export FIREBASE_PROJECT_ID="$(gcloud config get-value project)"
export CLOUDSQL_INSTANCE="$(gcloud config get-value project):asia-south1:foodbridge-pg"

AUTO_CREATE_TABLES=true ./deploy/deploy.sh \
  --cors-origins "$CORS_ORIGINS" \
  --firebase-project "$FIREBASE_PROJECT_ID" \
  --cloudsql "$CLOUDSQL_INSTANCE"

# Steady state
AUTO_CREATE_TABLES=false ./deploy/deploy.sh \
  --cors-origins "$CORS_ORIGINS" \
  --firebase-project "$FIREBASE_PROJECT_ID" \
  --cloudsql "$CLOUDSQL_INSTANCE"
```

The script mounts secret `foodbridge-database-url` → `DATABASE_URL`, sets production flags, and attaches Cloud SQL.

Update CORS after Hosting URLs are known (if different from `.web.app` defaults):

```bash
gcloud run services update foodbridge-rescueflow \
  --region=asia-south1 \
  --update-env-vars="CORS_ORIGINS=https://YOUR-donor.web.app,https://YOUR-recipient.web.app,https://YOUR-admin.web.app"
```

---

## 5. Deploy frontends (static site on Cloud Run)

```bash
# 1️⃣ Build each frontend (example using Vite)
cd frontend/donor   # repeat for recipient & admin or use a monorepo script
npm install
npm run build   # outputs to ./dist

# 2️⃣ Create a lightweight Docker image (nginx) for the built assets
cat > Dockerfile <<'EOF'
FROM nginx:stable-alpine
COPY dist/ /usr/share/nginx/html
EXPOSE 8080
EOF

# 3️⃣ Build and push the image
PROJECT=$(gcloud config get-value project)
docker build -t gcr.io/$PROJECT/foodbridge-donor-ui:latest .
docker push gcr.io/$PROJECT/foodbridge-donor-ui:latest

# 4️⃣ Deploy to Cloud Run (repeat for each UI image)
gcloud run deploy foodbridge-donor-ui \
  --image gcr.io/$PROJECT/foodbridge-donor-ui:latest \
  --region asia-south1 \
  --allow-unauthenticated \
  --port 8080
```

Or build each app manually from `frontend/*/ .env.production.example`.

---

## 6. Smoke test

```bash
URL=$(gcloud run services describe foodbridge-rescueflow --region=asia-south1 --format='value(status.url)')
./deploy/smoke_test.sh "$URL"
# Expect health 200; demo seed should be blocked (403) in production
```

Authenticated API checks require a real Firebase ID token (`Authorization: Bearer …`).

---

## 7. IAM (least privilege)

Runtime compute SA typically needs:

- `roles/secretmanager.secretAccessor` on `foodbridge-database-url`
- `roles/cloudsql.client`
- `roles/aiplatform.user` (if Gemini enabled)

Do **not** grant Owner/Editor to make deploy work.

---

## 8. Cost & cleanup

Charges while idle: Cloud SQL instance (largest), Artifact Registry, Vertex usage.

```bash
gcloud run services delete foodbridge-rescueflow --region=asia-south1
# gcloud sql instances delete foodbridge-pg   # destructive
```

---

## Local vs production auth

| Mode | Frontend | Backend |
|------|----------|---------|
| Local / Cloud Shell | `VITE_AUTH_MODE` unset → demo headers | `DEMO_MODE=true`, localhost CORS / Vite proxy |
| Production | `VITE_AUTH_MODE=firebase` + Bearer token | `DEMO_MODE=false`, `CORS_ORIGINS=https://…` |

Never enable demo headers on a public Cloud Run service.
