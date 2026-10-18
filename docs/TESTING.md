# Testing

## Acceptance test matrix

| Area | Test cases | Data / expected result | Verification |
|---|---|---|
| Demo seed | First seed, repeated seed, reset and reseed | Creates 11 synthetic recipients; repeat is idempotent; force replaces demo rows without duplicates. | Automated API |
| Donation validation | Valid donation; zero/negative portions; past deadline; timezone-naive deadline | Valid requests create donations; invalid requests return 422. | Automated API |
| Eligibility | Accepted category, unsupported category, inactive recipient, zero capacity, pickup after deadline | Only active recipients with capacity, compatible food, and feasible pickup time receive offers. D, I, J, and K exercise exclusion paths for vegetarian donations. | Automated service/API |
| Ranking and offers | Stable ordering/tie-break; capacity-ranked offers; total offers bounded by remaining portions | Offers are deterministic, positive, and never exceed available stock. | Automated service/API |
| Category coverage | Vegetarian/vegan/multi-category matches; meat-only match; mixed-food no-match | A-H cover vegetarian/vegan and other categories; K is meat-only; nobody accepts `mixed`. | Vegetarian/mixed automated API; vegan/meat manual |
| Invitation lifecycle | Accept; partial accept; full accept; decline; rematch; duplicate response; cancelled invitation response | Accept reduces stock/capacity exactly once; decline leaves stock unchanged and rematches others; invalid repeat responses return 409. | Automated service/API |
| Allocation and pickup | Partial/full allocation; confirm pickup; complete pickup | Allocated portions remain separate from confirmed/completed pickup metrics. | Allocation invariants automated; confirm/complete manual |
| Recovery and admin | Empty recovery queue; declined donation in queue; manual rematch; dashboard counts; audit trail | Only donations needing recovery appear in the queue; dashboard and audit reflect persisted events. | Empty/declined summaries and dashboard automated; rematch/audit manual |
| Invitation timeout job | Response timeout expires only due offers and rematches; pickup deadline expires all pending offers and the donation; rerunning is idempotent; late accept is rejected | Timed-out recipients are not re-invited, remaining portions are unchanged until accepted, and no matching occurs after the pickup deadline. | Automated service tests in `test_timeouts.py`; scheduled Cloud Run Job manual smoke test |
| AI explanation | Gemini success; missing config/credentials fallback; timeout/error fallback; no recovery-needed summary | Match explanation tries Gemini when configured. Recovery summary returns a fixed fallback immediately for an empty queue; with a donation needing recovery it calls Gemini and falls back if the call fails. | Fallback automated; live Gemini manual on Cloud Run |
| Authorization | Donor/admin/recipient allowed routes; wrong role; recipient attempting another recipient's invitation/allocation | Protected operations reject unauthorized users; recipient scope stays bound to that recipient. | Automated API plus manual recipient-scope check |
| Concurrency | Concurrent accepts against shared stock | PostgreSQL-only; total allocations and recipient capacity must never go negative or exceed available stock. | Automated PostgreSQL-only |
| Frontend | Main routes, demo seed/reset, donation form, role switch, accept/decline, pickup actions, error banners | UI reflects API state and labels synthetic/demo values. | Component tests plus manual E2E |

## Seeded recipient profiles

`POST /api/v1/demo/seed` creates synthetic recipient profiles only. It does not create donations, invitations, or allocations, so the recovery queue starts empty and can be tested as its own case. Create donations and respond to offers to build each lifecycle state.

| Recipient | Intended scenario |
|---|---|
| Community Kitchen A | 80-portion vegetarian offer; primary accept path. |
| Community Kitchen B | Smaller vegetarian capacity; alternate offer and rematch. |
| Community Kitchen C | Vegetarian capacity and distance variation for ranking. |
| Community Kitchen D | Accepts vegetarian food but cannot arrive before the typical two-hour deadline. |
| Neighborhood Pantry E | Multi-category recipient; vegetarian/vegan/bakery compatibility. |
| Family Meal Center F | High-capacity multi-category recipient; partial/full allocation scenarios. |
| Senior Support Kitchen G | Smaller multi-category capacity; alternate accept and ranking. |
| Campus Food Hub H | Multi-category recipient with different distance and preferences. |
| Zero-Capacity Kitchen I | Active and category-compatible, but must not receive an offer while capacity is zero. |
| Inactive Kitchen J | Has capacity and compatible categories, but must not receive an offer while inactive. |
| Meat-Only Pantry K | Active with capacity, but must not receive a vegetarian offer. |

Use a `vegan` donation to exercise multiple multi-category recipients, a `meat` donation to exercise the single-recipient K path, and a `mixed` donation to exercise the no-match path.

All distances and organizations are synthetic. The seed is not live routing, real recipient data, or an assertion that a real organization exists.

## Backend automated suite

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# Windows PowerShell: $env:PYTHONPATH = (Get-Location).Path
pytest -q
```

The API and service tests use in-memory SQLite. They cover health, validation, matching eligibility/ranking, offer bounds, invitation responses, rematching, allocation guards, pickup separation, authorization, and deterministic AI fallback. Live Gemini calls are not required by the automated suite.

### PostgreSQL concurrency suite

Use a disposable PostgreSQL database only:

```bash
# PowerShell: $env:CONCURRENCY_DATABASE_URL = "postgresql+psycopg2://USER:PASS@localhost:5432/foodbridge_test"
pip install psycopg2-binary
pytest tests/test_concurrency.py -q
```

Without `CONCURRENCY_DATABASE_URL`, the concurrency test is skipped.

## Frontend suite

```bash
cd frontend
npm install
npm test
npm run build
```

Component tests cover shell rendering, form presence, and demo warnings. Full browser E2E automation is not bundled.

## Manual end-to-end sequence

1. Start the API and frontend; from Admin, choose **Reset & reseed**.
2. As Donor, publish 120 vegetarian portions with a deadline about two hours away. Verify offers go only to eligible recipients; D, I, J, and K must not receive one. Confirm pending offer portions sum to no more than 120. Repeat with `vegan` (multi-category matches), `meat` (K only), and `mixed` (no match).
3. Leave a recipient offer unanswered for the configured response window (15 minutes by default). Verify the job marks it expired, records an audit event, and creates offers for other feasible recipients without changing remaining stock. Confirm the timed-out recipient is not re-invited.
4. Open the match explanation. With Vertex AI configured it should report `gemini`; with AI unavailable it should report `fallback` while retaining deterministic scores/reasons.
5. As a recipient with a pending offer, decline. Verify remaining stock is unchanged, that recipient is not re-invited, another eligible recipient is offered the stock, and Admin recovery/audit records the decline/rematch.
6. Accept a partial offer (Kitchen A has 80 capacity). Verify capacity/remaining portions decrease by the accepted amount, and other pending offers are rebalanced to no more than remaining stock.
7. Accept a remaining offer. Verify allocations never exceed 120 and the donation becomes allocated when stock reaches zero; stale pending offers are cancelled.
8. Confirm pickup, then complete pickup. Verify admin metrics distinguish allocated, pickup-confirmed, and pickup-completed portions.
9. With no donations needing recovery, open **AI recovery summary**. Current behavior returns the fixed empty-queue fallback without calling Gemini. For the AI-backed path, create another donation, decline an offer (or exhaust pending offers), then open the summary; it should report `gemini` when the model request succeeds and `fallback` if it fails.
10. Verify invalid donation requests (zero portions, past deadline, timezone-naive deadline), recipient isolation, donor/admin permissions, and recipient role restrictions.

## Deployment smoke check

Run `deploy/smoke_test.sh` against the deployed API to verify health and demo seeding. For Vertex AI, also verify the Cloud Run revision's project/model settings and service-account permissions, then exercise an AI-backed explanation with a donation that has recovery activity.

## Known limitations

- Vertex AI response quality/availability is not covered by deterministic CI tests; it requires configured credentials and a live service.
- Cloud SQL IAM authentication depends on deployment configuration.
- Frontend network retry behavior and full browser E2E are not automated.
