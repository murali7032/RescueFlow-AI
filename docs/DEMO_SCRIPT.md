# Demo Script (3–4 minutes) — RescueFlow AI by FoodBridge

**Prep (before stage):** start API (`uvicorn app.main:app --reload --port 8000`), seed from Admin → **Reset & reseed**, open Donor (:5173), Recipient (:5174), Admin (:5175).

---

### 0:00 — Hook (Admin)
> “Restaurants lose edible surplus every night—not because nobody wants it, but because the **first match fails**: declines, capacity limits, missed windows. RescueFlow AI recovers what’s left.”

Show dashboard banner: synthetic demo data · allocated ≠ meals served.

### 0:30 — Problem
> “A listing board stops at the first invite. We manage the **recovery lifecycle** after that invite fails.”

### 0:45 — Donor creates 120 portions (Donor app)
Narrate while submitting form:
- Harbor Bistro · vegetarian · **120 portions** · deadline ~2 hours · demo address.
- Click **Publish & match**.

**Expect:** donation created; ranked offers appear; Kitchen D absent (cannot collect before deadline); suggested portions sum ≤ 120.

### 1:20 — Explain ranking
Click **AI explanation**.  
**Expect:** summary (Gemini or fallback) with scores/reasons. Stress: AI explains; Python owns eligibility.

### 1:40 — Decline & recovery (Recipient)
Switch to Kitchen with a pending offer → **Decline**.  
**Expect:** toast that stock unchanged; rematch created.  
Admin recovery / audit shows decline + rematch.

### 2:10 — Partial accept
As Kitchen A (or top capacity) → **Accept**.  
**Expect:** ~80 portions allocated; pickup still **pending**; donation remaining ~40; other pending offers remain (rebalanced), not mass-cancelled.

### 2:40 — Second accept
Another kitchen accepts remaining offer.  
**Expect:** total allocations ≤ 120; remaining ≥ 0.

### 3:00 — Pickup separation
On an allocation → **Confirm pickup**.  
Admin: allocated vs pickup-confirmed diverge—prove meals aren’t auto-counted.

### 3:20 — Admin close
Point at recovery rate, declines, audit trail.  
> “RescueFlow doesn’t just match—it reallocates safely when the first path fails, without overselling a single portion.”

### 3:45 — Close
> “Synthetic demo today. Same ledger rules for production with Cloud SQL locks on Cloud Run.”
