#!/usr/bin/env bash
# Deploy RescueFlow AI backend to Cloud Run with Cloud SQL + Secret Manager.
#
# Usage:
#   export CORS_ORIGINS="https://foodbridge-ui-XXXX.a.run.app"
#   # Or temporarily: export CORS_ORIGINS="*"
#   export CLOUDSQL_INSTANCE="PROJECT:asia-south1:foodbridge-pg"   # optional
#   ./deploy/deploy.sh [--project ID] [--region REGION] [--service NAME]
#
# First-time DB bootstrap (optional once):
#   AUTO_CREATE_TABLES=true ./deploy/deploy.sh ...
set -euo pipefail

REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-foodbridge-rescueflow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUTO_CREATE_TABLES="${AUTO_CREATE_TABLES:-false}"
DEMO_MODE="${DEMO_MODE:-true}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --service) SERVICE="$2"; shift 2 ;;
    --cors-origins) CORS_ORIGINS="$2"; shift 2 ;;
    --cloudsql) CLOUDSQL_INSTANCE="$2"; shift 2 ;;
    --demo-mode) DEMO_MODE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

command -v gcloud >/dev/null || { echo "gcloud CLI required"; exit 1; }

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "No GCP project configured. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

CORS_ORIGINS="${CORS_ORIGINS:-}"

if [[ -z "${CORS_ORIGINS}" ]]; then
  echo "ERROR: CORS_ORIGINS is required for production deploy."
  echo "Example (after frontends are deployed):"
  echo "  export CORS_ORIGINS='https://foodbridge-ui-XXXX.a.run.app'"
  echo "Or for first boot before UI URLs exist:"
  echo "  export CORS_ORIGINS='*'"
  echo "  ./deploy/deploy.sh"
  exit 1
fi

if [[ "${CORS_ORIGINS}" == "*" ]]; then
  echo "WARNING: CORS_ORIGINS set to '*', all origins will be allowed."
fi

if [[ "${DEMO_MODE}" == "true" ]]; then
  echo "WARNING: DEMO_MODE=true — X-Demo-Role headers are accepted (cup / demo deploy)."
fi

echo "==> Project:           ${PROJECT_ID}"
echo "==> Region:            ${REGION}"
echo "==> Service:           ${SERVICE}"
echo "==> CORS_ORIGINS:      ${CORS_ORIGINS}"
echo "==> DEMO_MODE:         ${DEMO_MODE}"
echo "==> AUTO_CREATE_TABLES:${AUTO_CREATE_TABLES}"

echo "==> Enabling required APIs (idempotent)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  aiplatform.googleapis.com \
  --project="${PROJECT_ID}"

echo "==> Existing Cloud Run services in ${REGION}:"
gcloud run services list --region="${REGION}" --project="${PROJECT_ID}" || true

if ! gcloud secrets describe foodbridge-database-url --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "ERROR: Secret 'foodbridge-database-url' not found."
  echo "Create Cloud SQL credentials first:"
  echo "  CONN=\"${PROJECT_ID}:${REGION}:foodbridge-pg\""
  echo "  printf 'postgresql+psycopg2://USER:PASS@/foodbridge?host=/cloudsql/%s' \"\$CONN\" | \\"
  echo "    gcloud secrets create foodbridge-database-url --data-file=- --project=${PROJECT_ID}"
  exit 1
fi

# Grant runtime SA access to the secret (idempotent-ish)
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
RUNTIME_SA="${RUNTIME_SA:-${PROJECT_NUMBER}-compute@developer.gserviceaccount.com}"
echo "==> Ensuring Secret Accessor on ${RUNTIME_SA}"
gcloud secrets add-iam-policy-binding foodbridge-database-url \
  --project="${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor" \
  --quiet >/dev/null || true

# Use @ delimiter so CORS_ORIGINS may contain commas.
ENV_VARS="^@^ENVIRONMENT=production"
ENV_VARS+="@DEMO_MODE=${DEMO_MODE}"
ENV_VARS+="@AUTO_CREATE_TABLES=${AUTO_CREATE_TABLES}"
ENV_VARS+="@DOCS_ENABLED=false"
ENV_VARS+="@GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
ENV_VARS+="@GOOGLE_CLOUD_LOCATION=${REGION}"
ENV_VARS+="@GOOGLE_GENAI_USE_VERTEXAI=true"
ENV_VARS+="@GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.5-flash}"
ENV_VARS+="@AI_ENABLED=true"
ENV_VARS+="@INVITATION_RESPONSE_TIMEOUT_MINUTES=${INVITATION_RESPONSE_TIMEOUT_MINUTES:-15}"
ENV_VARS+="@CORS_ORIGINS=${CORS_ORIGINS}"

DEPLOY_ARGS=(
  run deploy "${SERVICE}"
  --source "${ROOT_DIR}/backend"
  --region "${REGION}"
  --project "${PROJECT_ID}"
  --allow-unauthenticated
  --set-env-vars "${ENV_VARS}"
  --set-secrets "DATABASE_URL=foodbridge-database-url:latest"
  --memory 512Mi
  --cpu 1
  --timeout 60
  --concurrency 40
  --min-instances 0
  --max-instances 10
  --quiet
)

if [[ -n "${CLOUDSQL_INSTANCE:-}" ]]; then
  echo "==> Attaching Cloud SQL: ${CLOUDSQL_INSTANCE}"
  DEPLOY_ARGS+=(--add-cloudsql-instances "${CLOUDSQL_INSTANCE}")
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet >/dev/null 2>&1 || true
else
  echo "==> WARNING: CLOUDSQL_INSTANCE not set. Pass --cloudsql PROJECT:REGION:INSTANCE"
  echo "    if DATABASE_URL uses /cloudsql/ socket."
fi

echo "==> Building and deploying backend..."
gcloud "${DEPLOY_ARGS[@]}"

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/aiplatform.user" \
  --condition=None \
  --quiet >/dev/null 2>&1 || true

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo "==> Deployed: ${URL}"
echo "==> Health:   ${URL}/health"
echo ""
echo "Next:"
echo "  1. export VITE_API_URL=${URL}"
echo "  2. ./deploy/deploy_frontend.sh   # deploys unified foodbridge-ui to Cloud Run"
echo "  3. Update CORS_ORIGINS to the foodbridge-ui URL, then update backend"
echo "  4. ./deploy/smoke_test.sh ${URL}"
echo "  5. After schema exists, keep AUTO_CREATE_TABLES=false"
