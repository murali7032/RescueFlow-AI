#!/usr/bin/env bash
# Build all frontends against a Cloud Run API URL and deploy each to Cloud Run.
#
# Usage:
#   export VITE_API_URL="https://foodbridge-rescueflow-XXXX.a.run.app"
#   ./deploy/deploy_frontend.sh [--project ID] [--region REGION]
#
# Optional:
#   VITE_AUTH_MODE=demo   (default — demo role headers; no Firebase)
set -euo pipefail

REGION="${REGION:-asia-south1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
VITE_AUTH_MODE="${VITE_AUTH_MODE:-demo}"
AR_REPO="${AR_REPO:-foodbridge}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

: "${VITE_API_URL:?Set VITE_API_URL to your Cloud Run API URL}"

echo "=============================================="
echo " RescueFlow frontend → Cloud Run (NOT Firebase)"
echo "=============================================="

# Hard fail if an old Firebase Hosting layout is still present
if [[ -f "${ROOT_DIR}/firebase.json" || -f "${ROOT_DIR}/.firebaserc" ]]; then
  echo "ERROR: firebase.json / .firebaserc still present."
  echo "This script no longer uses Firebase Hosting."
  echo "Run: git pull origin main   (or delete those files) and re-run."
  exit 1
fi

command -v gcloud >/dev/null || { echo "gcloud CLI required"; exit 1; }

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "No GCP project configured. Run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "==> Project:       ${PROJECT_ID}"
echo "==> Region:        ${REGION}"
echo "==> VITE_API_URL:  ${VITE_API_URL}"
echo "==> VITE_AUTH_MODE:${VITE_AUTH_MODE}"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --project="${PROJECT_ID}"

if ! gcloud artifacts repositories describe "${AR_REPO}" \
  --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "==> Creating Artifact Registry repo: ${AR_REPO}"
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --project="${PROJECT_ID}" \
    --description="FoodBridge / RescueFlow UI images"
fi

write_env() {
  local app_dir="$1"
  cat > "${app_dir}/.env.production" <<EOF
VITE_API_URL=${VITE_API_URL}
VITE_AUTH_MODE=${VITE_AUTH_MODE}
EOF
}

UI_URLS=()

for app in donor recipient admin; do
  service="foodbridge-${app}-ui"
  image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${service}:latest"

  echo "==> Building ${app} (.env.production)"
  write_env "${FRONTEND_DIR}/${app}"

  echo "==> Cloud Build → ${image}"
  gcloud builds submit "${FRONTEND_DIR}" \
    --project="${PROJECT_ID}" \
    --config="${ROOT_DIR}/deploy/cloudbuild-frontend.yaml" \
    --substitutions="_APP=${app},_VITE_API_URL=${VITE_API_URL},_VITE_AUTH_MODE=${VITE_AUTH_MODE},_IMAGE=${image}"

  echo "==> Deploying Cloud Run service ${service}"
  gcloud run deploy "${service}" \
    --image="${image}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --allow-unauthenticated \
    --port=8080 \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=5 \
    --quiet

  url="$(gcloud run services describe "${service}" \
    --region="${REGION}" --project="${PROJECT_ID}" \
    --format='value(status.url)')"
  UI_URLS+=("${url}")
  echo "==> ${app}: ${url}"
done

CORS_JOINED="$(IFS=,; echo "${UI_URLS[*]}")"

echo ""
echo "==> All UIs deployed on Cloud Run."
echo "Set API CORS to these origins and redeploy the backend:"
echo ""
echo "  export CORS_ORIGINS='${CORS_JOINED}'"
echo "  ./deploy/deploy.sh --cors-origins \"\$CORS_ORIGINS\" --cloudsql \"\${PROJECT_ID}:asia-south1:foodbridge-pg\""
echo ""
echo "Or update in place:"
echo "  gcloud run services update foodbridge-rescueflow \\"
echo "    --region=${REGION} \\"
echo "    --update-env-vars=\"CORS_ORIGINS=${CORS_JOINED}\""
