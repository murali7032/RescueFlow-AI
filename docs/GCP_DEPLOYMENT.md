# Google Cloud Deployment Guide (Cloud Shell)

Region default: **asia-south1**. Use your existing project — never invent project IDs.

## 1. Select project and region

```bash
gcloud config get-value project
# If empty:
# gcloud config set project YOUR_PROJECT_ID
gcloud config set run/region asia-south1
```

## 2. Inspect existing Cloud Run services

```bash
gcloud run services list --region=asia-south1
```

If a service named `foodbridge` already exists, decide whether to update it or deploy as `foodbridge-rescueflow` (default in `deploy/deploy.sh`) to avoid overwriting unrelated workloads.

## 3. Enable APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  aiplatform.googleapis.com
```

## 4. Database (Cloud SQL PostgreSQL)

```bash
# Create instance only if you do not already have one (costs apply while running)
gcloud sql instances create foodbridge-pg \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=asia-south1

gcloud sql databases create foodbridge --instance=foodbridge-pg
gcloud sql users create foodbridge --instance=foodbridge-pg --password=GENERATE_A_STRONG_PASSWORD
```

Store connection string in Secret Manager:

```bash
PROJECT=$(gcloud config get-value project)
CONN="${PROJECT}:asia-south1:foodbridge-pg"
printf 'postgresql+psycopg2://foodbridge:PASSWORD@/foodbridge?host=/cloudsql/%s' "$CONN" | \
  gcloud secrets create foodbridge-database-url --data-file=-
```

## 5. Deploy backend

From repo root (Cloud Shell clone of this repository):

```bash
chmod +x deploy/deploy.sh deploy/smoke_test.sh
./deploy/deploy.sh --service foodbridge-rescueflow --region asia-south1
```

Attach Cloud SQL (after first deploy if needed):

```bash
PROJECT=$(gcloud config get-value project)
gcloud run services update foodbridge-rescueflow \
  --region=asia-south1 \
  --add-cloudsql-instances=${PROJECT}:asia-south1:foodbridge-pg \
  --update-secrets=DATABASE_URL=foodbridge-database-url:latest \
  --set-env-vars=ENVIRONMENT=production,DEMO_MODE=false,AUTO_CREATE_TABLES=true
```

## 6. Smoke test

```bash
URL=$(gcloud run services describe foodbridge-rescueflow --region=asia-south1 --format='value(status.url)')
./deploy/smoke_test.sh "$URL"
curl -s "$URL/health"
```

## 7. Frontend (Firebase Hosting — optional)

```bash
# Install Firebase CLI if needed
npm install -g firebase-tools
firebase login
```

For each app (`donor`, `recipient`, `admin`):

```bash
cd frontend/donor
echo "VITE_API_URL=$URL" > .env.production
npm install && npm run build
```

Configure three Hosting sites or three directories in `firebase.json` pointing at each `dist/`. Set rewrite to `index.html` for SPA refresh.

**Manual console steps:** create Firebase project (can share GCP project), enable Hosting, add web apps, copy config. For Authentication, enable Email/Google providers and set custom claims `role` / `recipient_id` via Admin SDK — until then use local demo headers only (`DEMO_MODE` must stay false in production API).

## 8. Vertex AI / Gemini

Grant the Cloud Run runtime service account `roles/aiplatform.user`. Set:

- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION=asia-south1`
- `GOOGLE_GENAI_USE_VERTEXAI=true`
- `AI_ENABLED=true`

If model access fails, API explanations fall back automatically.

## 9. IAM notes

Prefer least privilege:

- Cloud Run invoker (if private)
- Secret Accessor on specific secrets
- Cloud SQL Client
- Vertex AI User

If source deploy fails with Cloud Build permission errors, grant the Cloud Build service account `roles/run.admin` and `roles/iam.serviceAccountUser` on the runtime SA — not project Owner.

## 10. Cost drivers & cleanup

Idle cost drivers: Cloud SQL instance, Cloud Run (minimal when scaled to zero), Artifact Registry images, Vertex usage.

Cleanup demo resources:

```bash
gcloud run services delete foodbridge-rescueflow --region=asia-south1
# Only if created solely for this demo:
# gcloud sql instances delete foodbridge-pg
```

## Temporary alternative

If Cloud SQL blocks the demo, deploy with SQLite **ephemeral** disk (`DATABASE_URL=sqlite:////tmp/foodbridge.db`) — data resets on new revisions and **does not** provide production concurrency. Label this clearly; do not claim Cloud SQL guarantees.
