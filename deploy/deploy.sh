#!/usr/bin/env bash
# Deploy RescueFlow AI backend to Cloud Run (asia-south1 by default).
# Usage: ./deploy/deploy.sh [--project PROJECT_ID] [--region REGION] [--service SERVICE]
set -euo pipefail

REGION="${REGION:-asia-south1}"
SERVICE="${SERVICE:-foodbridge-rescueflow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --service) SERVICE="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

command -v gcloud >/dev/null || { echo "gcloud CLI required"; exit 1; }

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "No GCP project configured. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "==> Project: ${PROJECT_ID}"
echo "==> Region:  ${REGION}"
echo "==> Service: ${SERVICE}"

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

if gcloud run services describe "${SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "==> Updating existing service ${SERVICE}"
else
  echo "==> Creating new service ${SERVICE}"
fi

# Optional secrets — create empty placeholders only if missing (manual values required)
ensure_secret() {
  local name="$1"
  if ! gcloud secrets describe "${name}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Creating secret shell: ${name} (set value manually before production use)"
    printf 'CHANGE_ME' | gcloud secrets create "${name}" --data-file=- --project="${PROJECT_ID}"
  fi
}

# DATABASE_URL should already exist for production; do not overwrite.
if ! gcloud secrets describe foodbridge-database-url --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "WARNING: secret foodbridge-database-url missing."
  echo "Create it with your Cloud SQL connection string before relying on persistence."
  echo "Example:"
  echo "  printf 'postgresql+psycopg2://USER:PASS@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE' | \\"
  echo "    gcloud secrets create foodbridge-database-url --data-file=-"
fi

echo "==> Building and deploying backend from source..."
gcloud run deploy "${SERVICE}" \
  --source "${ROOT_DIR}/backend" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,DEMO_MODE=false,AUTO_CREATE_TABLES=true,GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},AI_ENABLED=true" \
  --quiet

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"
echo "==> Deployed: ${URL}"
echo "==> Health:   ${URL}/health"
echo "Run: ./deploy/smoke_test.sh ${URL}"
