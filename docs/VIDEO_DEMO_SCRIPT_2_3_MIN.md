# RescueFlow AI by FoodBridge — 2–3 minute video demo

**Target runtime:** about 2:40, including short pauses for screen actions  
**Audience:** Google AI Builder Cup review panel  
**Demo route:** Dashboard → Donor Workspace → AI explanation → Recipient Workspace → Admin Dashboard

## Before recording

- Use a seeded demo environment with synthetic rows. Do not reset or mutate live production data for the recording.
- Make sure the UI and backend are on the revisions you intend to demonstrate. Test the Gemini explanation once before recording; only call it a Gemini explanation when the UI identifies the source as Gemini.
- Prepare one donation with a pending offer and one recipient that can decline it. If you want to demonstrate acceptance too, prepare a second pending offer. Keep the donation and recipient names clearly marked as demo data.
- Close browser tabs and hide personal account details. Record at 1080p if available, zoom the browser to about 110–125%, and move the pointer slowly.

## Timed narration and screen actions

### 0:00–0:20 — Opening and agenda

**On screen:** Dashboard; briefly show the FoodBridge / RescueFlow name and the synthetic-data notice.

**Say:**

> “Hello, we’re ProblemSolvers, and this is RescueFlow AI by FoodBridge. I’ll show the food recovery problem, the donor-to-recipient workflow, how Gemini helps, and our limitations and next steps.”

### 0:20–0:42 — The problem and the idea

**On screen:** Dashboard impact metrics. Point to allocated versus pickup-completed values.

**Say:**

> “Good food can be lost when the first recipient declines, has limited capacity, or misses the pickup window. RescueFlow continues recovery after that first offer while protecting the donor’s portion count.”

### 0:42–1:12 — Donor publishes and sees ranked offers

**On screen:** Donor Workspace. Enter a demo donation—for example, 96 vegetarian portions with a clear pickup deadline—then select **Publish & match**. Show the ranked recipient offers and scores.

**Say:**

> “The donor records the food, quantity, category, pickup details, and deadline. RescueFlow filters eligible recipients and ranks feasible offers by capacity, timing, preferences, and estimated distance. Offer quantities stay within available stock. Distance here is synthetic, not live route calculation.”

### 1:12–1:35 — Gemini explanation

**On screen:** Select the donation and click **AI explanation**. Pause on a successful response marked **Gemini**; point out the offer reason and next step.

**Say:**

> “Gemini through Vertex AI turns matching facts into a plain-language explanation: why an offer fits and what response is pending. The backend’s deterministic rules decide eligibility and reserve portions. Gemini explains the decision; it does not control the food ledger.”

**Optional voiceover if the screen transition is quick:**

> “The API and timeout worker run on Cloud Run, Cloud SQL stores the allocation state, and Cloud Scheduler triggers timeout checks.”

### 1:35–2:05 — Recipient response and recovery

**On screen:** Open Recipient Workspace, choose a kitchen with a pending offer, and select **Decline**. Show the confirmation that stock remains unchanged. Then show the refreshed or rematched offers in Donor Workspace or the Admin recovery queue.

**Say:**

> “A decline does not allocate those portions. RescueFlow records it and recalculates feasible offers. The timeout job can also rematch unanswered invitations while the pickup deadline is still open. The goal is to recover remaining food without restarting the process manually.”

### 2:05–2:25 — Allocation is not pickup

**On screen:** If a suitable pending offer is available, accept it as that recipient. Show the allocation and its pickup status; point out the separate pickup confirmation/completion controls or dashboard values.

**Say:**

> “Acceptance revalidates stock and recipient capacity. Allocation is not collection: pickup confirmation and completion are tracked separately, so the dashboard distinguishes reserved portions from food actually handed off.”

### 2:25–2:45 — Limitations, future goals, close

**On screen:** Admin dashboard, then end on the project name or live prototype URL.

**Say:**

> “This prototype uses synthetic recipients, estimated distances, and demo-role access; it is not ready for production identity or partner onboarding. Next, we want to add live routing and reliable notifications, then pilot with local donors and kitchens and measure food actually collected. RescueFlow brings a practical food-sharing mission together with Gemini explanations and auditable allocation. Thank you.”

## Recording and submission checklist

- Keep the final video between 2 and 3 minutes; trim pauses while keeping the narration natural.
- Show only synthetic/demo records and avoid claiming prototype portions represent real meals rescued.
- If the explanation card says **Fallback** or Gemini is unavailable, do not describe that card as a Gemini response. Re-record that segment after confirming a successful Gemini response.
- Upload the MP4 to the submission-approved host (for example, Google Drive or YouTube as an unlisted video), verify the link in a private/incognito window, and submit that share link. No video has been uploaded by this project script.
