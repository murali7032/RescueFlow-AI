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

## 7. Invitation timeout and rematch job

The API assigns each invitation an expiry of `min(created_at + response timeout, donation pickup deadline)`. A Cloud Run Job scans due invitations and deadline-expired donations, expires them, and rematches remaining portions only when there is still time to collect. The default response timeout is 15 minutes and can be changed with `INVITATION_RESPONSE_TIMEOUT_MINUTES`.

### Deploy safely from the Google Cloud Console

Apply the schema migrations **before** deploying the new API image:

1. Open **Cloud SQL → your PostgreSQL instance → Studio** and connect to the `foodbridge` database.
2. Run `backend/app/db/migrations/20261018_invitation_expiry.sql`, then `backend/app/db/migrations/20261018_donor_reviews.sql` from this repository in Cloud SQL Studio. These add/backfill invitation expiry, donor type, and the review table. Existing pending invitations older than 15 minutes may be expired on the first job run. Donor trust score is the average recipient rating scaled to 100 (50 before the first review); at least three reviews averaging 2 stars or lower pause new submissions under that donor name.
3. Build the new backend image so it contains both the API changes and `app.workers.invitation_timeout_worker`. In **Cloud Build → Triggers**, run the backend build trigger for the commit containing this change. Configure its build file as `deploy/cloudbuild-backend.yaml`; set `_REGION`, `_REPOSITORY`, and `_IMAGE` to the Artifact Registry region, repository, and image name you use. This build file builds and pushes the image; it does not deploy the service automatically.
4. In **Cloud Run → Services → `foodbridge-rescueflow` → Edit and deploy new revision**, select the newly built Artifact Registry image. Keep the existing Cloud SQL connection, database secret, and service account. Set or confirm `INVITATION_RESPONSE_TIMEOUT_MINUTES=15`, `AI_ENABLED=true`, `GEMINI_MODEL=gemini-3.5-flash`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=asia-south1`, and `GOOGLE_GENAI_USE_VERTEXAI=true`. Deploy and confirm the new revision receives traffic.
5. Rebuild and redeploy the UI because the recipient workspace now displays each offer's response deadline. In **Cloud Build → Triggers**, create or run a frontend build trigger from the repository root using `deploy/cloudbuild-frontend.yaml`; set `_VITE_API_URL` to the backend Cloud Run URL, `_VITE_AUTH_MODE` to `demo`, and `_IMAGE` to your Artifact Registry image path with a tag. Then in **Cloud Run → Services → `foodbridge-ui` → Edit and deploy new revision**, select that image and deploy. The frontend build config uses `frontend/` as its build directory.
6. In **Cloud Run → Jobs → Create Job**, use the backend image from step 3. Set the container command to `python` and arguments to `-m app.workers.invitation_timeout_worker`. Configure the job with the same Cloud SQL instance, `DATABASE_URL` secret, and a service account that has `roles/cloudsql.client` and Secret Manager access. Set `ENVIRONMENT=production`, `AUTO_CREATE_TABLES=false`, and `INVITATION_RESPONSE_TIMEOUT_MINUTES=15`. Use one task and a short task timeout (for example, two minutes).
7. Grant the Cloud Scheduler trigger service account permission to execute this job (`roles/run.invoker` on the job). The job's runtime service account is separate: it needs database and secret access, not scheduler permissions.
8. Open the job's **Triggers** tab and choose **Add Scheduler Trigger**. Schedule it every minute (`* * * * *`) in UTC. Save the trigger, then run the job once manually to verify it connects and logs `Invitation timeout sweep complete`.
9. In staging, create a donation, leave an offer unanswered for 15 minutes, then check the Cloud Run Job execution logs, invitation state, audit events, and rematched offers. Confirm remaining stock is unchanged until a recipient accepts and that the timed-out recipient is not re-invited.

If your service already builds from a connected source repository, use its Cloud Build trigger to produce the updated image. Editing only Cloud Run environment variables does not put the new worker code into the image. Cloud Scheduler can trigger Cloud Run Jobs directly through the Console's job trigger workflow; see [Google's scheduled job guide](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule).

## 8. Cost & cleanup

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
