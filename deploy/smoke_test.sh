#!/usr/bin/env bash
# Smoke-test a deployed (or local) RescueFlow API.
# Usage: ./deploy/smoke_test.sh [BASE_URL]
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
BASE_URL="${BASE_URL%/}"

echo "==> Smoke testing ${BASE_URL}"

curl -fsS "${BASE_URL}/health" | tee /tmp/fb-health.json
echo
curl -fsS "${BASE_URL}/api/v1/health" >/dev/null

# Demo seed is blocked in production (DEMO_MODE=false). Skip if 403.
SEED_CODE="$(curl -s -o /tmp/fb-seed.json -w '%{http_code}' \
  -X POST "${BASE_URL}/api/v1/demo/seed" \
  -H 'Content-Type: application/json' \
  -H 'X-Demo-Role: admin')" || true

if [[ "${SEED_CODE}" == "200" ]]; then
  echo "==> Demo seed OK"
  DEADLINE="$(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+2H +%Y-%m-%dT%H:%M:%SZ)"
  CREATE_CODE="$(curl -s -o /tmp/fb-donation.json -w '%{http_code}' \
    -X POST "${BASE_URL}/api/v1/donations" \
    -H 'Content-Type: application/json' \
    -H 'X-Demo-Role: donor' \
    -d "{\"donor_name\":\"Smoke Test Cafe\",\"category\":\"vegetarian\",\"total_portions\":120,\"pickup_deadline\":\"${DEADLINE}\",\"is_demo\":true}")"
  echo "==> Create donation HTTP ${CREATE_CODE}"
  cat /tmp/fb-donation.json
  echo
else
  echo "==> Demo seed skipped/blocked (HTTP ${SEED_CODE}) — expected for production"
fi

echo "==> Smoke test finished"
