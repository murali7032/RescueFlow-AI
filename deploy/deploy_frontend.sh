#!/usr/bin/env bash
# Build all frontends against a Cloud Run API URL and deploy to Firebase Hosting.
#
# Usage:
#   export VITE_API_URL="https://foodbridge-rescueflow-xxxx.a.run.app"
#   export VITE_AUTH_MODE=firebase
#   # plus VITE_FIREBASE_* from the Firebase console
#   ./deploy/deploy_frontend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

: "${VITE_API_URL:?Set VITE_API_URL to your Cloud Run service URL}"

command -v firebase >/dev/null || { echo "firebase-tools required (npm i -g firebase-tools)"; exit 1; }
command -v npm >/dev/null || { echo "npm required"; exit 1; }

if [[ ! -f "${ROOT_DIR}/.firebaserc" ]]; then
  echo "Copy .firebaserc.example to .firebaserc and set your Firebase project id."
  exit 1
fi

write_env() {
  local app_dir="$1"
  cat > "${app_dir}/.env.production" <<EOF
VITE_API_URL=${VITE_API_URL}
VITE_AUTH_MODE=${VITE_AUTH_MODE:-firebase}
VITE_FIREBASE_API_KEY=${VITE_FIREBASE_API_KEY:-}
VITE_FIREBASE_AUTH_DOMAIN=${VITE_FIREBASE_AUTH_DOMAIN:-}
VITE_FIREBASE_PROJECT_ID=${VITE_FIREBASE_PROJECT_ID:-}
VITE_FIREBASE_APP_ID=${VITE_FIREBASE_APP_ID:-}
EOF
}

for app in donor recipient admin; do
  echo "==> Building ${app}"
  write_env "${ROOT_DIR}/frontend/${app}"
  (cd "${ROOT_DIR}/frontend/${app}" && npm install && npm run build)
done

echo "==> Deploying Firebase Hosting sites"
(cd "${ROOT_DIR}" && firebase deploy --only hosting)

echo "==> Done. Set Cloud Run CORS_ORIGINS to these Hosting URLs, then redeploy backend if needed."
