# Testing

## Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=%CD%   # Windows
# export PYTHONPATH=$PWD
pytest -q
```

Uses in-memory SQLite via `tests/conftest.py`. Covers health, donation validation, matching eligibility/ranking, accept/decline, rematch, over-allocation guards, pickup separation, authz, AI fallback.

### Concurrency (PostgreSQL required)

```bash
# Disposable DB only
set CONCURRENCY_DATABASE_URL=postgresql+psycopg2://USER:PASS@localhost:5432/foodbridge_test
pip install psycopg2-binary
pytest tests/test_concurrency.py -q
```

Without Postgres, the concurrency test is **skipped**.

## Frontend

```bash
cd frontend && npm install && npm test && npm run build
```

Component tests cover shell rendering, form presence, demo warnings. Full E2E browser automation is not bundled; use `deploy/smoke_test.sh` against a running API.

## Manual E2E demo sequence

1. `POST /api/v1/demo/seed`
2. Create donation 120 vegetarian portions, deadline +2h
3. Confirm Kitchen D excluded; offers ≤ 120
4. Decline one invitation → remaining still 120 → rematch
5. Accept top offer → remaining decreases; other pendings stay if stock remains
6. Accept second offer if stock remains → total allocations ≤ 120
7. Confirm pickup on allocation → dashboard pickup metrics move; allocated ≠ completed until completed status

## Known untested areas

- Live Vertex Gemini responses (fallback is tested)
- Cloud SQL IAM auth paths
- Frontend network-error retry UX beyond banners
