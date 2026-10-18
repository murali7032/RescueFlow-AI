"""Gemini / ADK-compatible explanation agent with deterministic fallback.

The model never allocates portions or mutates the database. It only
explains rankings and suggests recovery actions from provided snapshots.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.agent.tools import get_donation_snapshot, get_recipient_name
from app.config import get_settings

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = """You are FoodBridge RescueFlow's operational explainer. Explain matching and recovery decisions to a busy donor or administrator in plain, respectful language.

Use only the supplied facts. Never invent a recipient, reason, quantity, deadline, status, or outcome. Do not change allocations or imply that an offer is accepted when it is only pending. A match score is a relative ranking score out of 100, not a probability or guarantee. Distinguish an invitation, an allocation, and a confirmed/completed pickup.

For a donation explanation, state the current status and portions remaining; explain the top pending offer(s) with the score and the strongest supplied reasons (fit, capacity, collection timing, and estimated distance when present); explain what happens next and give one practical next step. For an admin recovery summary, state the number of affected donations and portions at risk, explain why the listed donations need attention, and clarify the next operational action. If there is no recovery work, say so clearly and explain that pending offers are still awaiting responses or no remaining stock needs a rematch, only when the facts support it.

Explain clearly using only the supplied facts. Include the current status, the most relevant reasons, and the next step when those facts are available. Choose the amount of detail that best helps the reader; there is no required word count, sentence count, or response length. Do not invent missing facts. Distinguish an invitation, an allocation, and a confirmed/completed pickup. Do not show raw database fields or ISO timestamps; express dates and times in readable form if needed."""


def _format_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc)
        hour = parsed.strftime("%I:%M %p").lstrip("0")
        return f"{parsed.strftime('%b %d, %Y')} at {hour} UTC"
    except (TypeError, ValueError):
        return None


def _friendly_reasons(reasons: list[str]) -> list[str]:
    friendly = []
    for reason in reasons:
        time_match = re.fullmatch(r"Can collect by (.+?) before deadline (.+)", reason)
        if time_match:
            collect_by = _format_time(time_match.group(1))
            deadline = _format_time(time_match.group(2))
            if collect_by and deadline:
                friendly.append(
                    f"can collect by {collect_by}, ahead of the {deadline} deadline"
                )
        elif reason.startswith("Capacity ") and reason.endswith(" portions available"):
            amount = reason.removeprefix("Capacity ").removesuffix(" portions available")
            friendly.append(f"has capacity for {amount} portions")
        elif reason.startswith("Synthetic distance ~"):
            distance = reason.removeprefix("Synthetic distance ~").removesuffix(
                " from pickup"
            )
            friendly.append(f"is an estimated {distance} km from pickup")
        elif reason.startswith("Prefers "):
            friendly.append(reason[0].lower() + reason[1:])
    return friendly


def _usable_explanation(text: str | None) -> tuple[str | None, str | None]:
    if not text or not text.strip():
        return None, "Gemini returned an empty response"
    cleaned = " ".join(text.strip().split()).strip('"“”')
    if not cleaned:
        return None, "Gemini returned an empty response"
    return cleaned, None


async def _generate_explanation(prompt: str) -> str | None:
    """Ask Gemini for a bounded answer, retrying once if its draft misses limits."""
    draft = await _call_gemini(prompt)
    accepted, reason = _usable_explanation(draft)
    if accepted:
        return accepted
    logger.info("Gemini explanation needs a rewrite: %s", reason)
    retry_prompt = (
        f"{prompt}\n\n"
        f"Your previous attempt returned no usable text ({reason}). Please answer "
        "the request directly using the supplied facts. Do not invent missing "
        "information. Choose a natural amount of detail; there is no required "
        "word count, sentence count, or response length."
    )
    retry = await _call_gemini(retry_prompt)
    accepted, reason = _usable_explanation(retry)
    if accepted:
        return accepted
    logger.warning("Gemini explanation failed validation after retry: %s", reason)
    return None


def _fallback_explain(snapshot: dict, db: Session) -> dict[str, Any]:
    matches = snapshot.get("matches") or []
    donation = snapshot["donation"]
    remaining = donation["remaining_portions"]
    total = donation["total_portions"]
    lines = [
        f"Donation #{donation['id']} from {donation['donor_name']} has "
        f"{remaining} of {total} {donation['category']} portions remaining. "
        f"Its current status is {donation['status'].replace('_', ' ')}."
    ]
    pending = [m for m in matches if m.get("status") == "pending"]
    declined = [m for m in matches if m.get("status") == "declined"]
    accepted = [m for m in matches if m.get("status") == "accepted"]

    if pending:
        lines.append("The highest-ranked pending offers are:")
        for rank, m in enumerate(pending[:3], start=1):
            name = get_recipient_name(db, m["recipient_id"])
            reasons = _friendly_reasons(m.get("reasons") or [])
            reason_text = "; ".join(reasons[:3])
            details = f" Reasons: {reason_text}." if reason_text else ""
            expires = _format_time(m.get("expires_at"))
            response_due = (
                f" The offer is awaiting a response by {expires}."
                if expires
                else " The offer is awaiting a response."
            )
            lines.append(
                f"{name} is ranked #{rank} with a match score of "
                f"{m['score']}/100 and an offer for {m['suggested_portions']} portions."
                f"{details}{response_due}"
            )
    if declined:
        lines.append(
            f"{len(declined)} decline(s) recorded — stock was not reduced; "
            "recovery rematching fills remaining capacity."
        )
    if accepted:
        lines.append(
            f"{len(accepted)} recipient offer(s) have been accepted and allocated. "
            "Pickup is a separate step and is not complete until it is confirmed."
        )

    actions: list[str] = []
    if donation["remaining_portions"] > 0 and not pending:
        actions.append(
            "Run recovery matching for the remaining portions if the pickup deadline is still open."
        )
    if pending:
        actions.append(
            "Wait for the recipient response; if the offer expires, the timeout job can rematch the remaining portions before the pickup deadline."
        )
    if declined:
        actions.append(
            "Review the declines; recipients who already declined are not automatically invited again."
        )
    if not actions:
        actions.append("Monitor pickup confirmation for the accepted allocation.")

    return {
        "source": "fallback",
        "summary": " ".join(lines),
        "matches": matches,
        "suggested_actions": actions,
    }


async def _call_gemini(prompt: str) -> str | None:
    settings = get_settings()
    if not settings.ai_enabled or not settings.google_cloud_project:
        return None

    try:
        # google-genai SDK (Vertex via GOOGLE_GENAI_USE_VERTEXAI)
        from google import genai
        from google.genai import types
    except ImportError:
        logger.info("google-genai not installed; using fallback explanations")
        return None

    try:
        client = genai.Client(
            vertexai=settings.google_genai_use_vertexai,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )

        def _generate() -> str:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                ),
            )
            return (response.text or "").strip()

        return await asyncio.wait_for(
            asyncio.to_thread(_generate),
            timeout=settings.ai_timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("Gemini timed out after %ss", settings.ai_timeout_seconds)
        return None
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return None


async def explain_match(db: Session, donation_id: int) -> dict[str, Any]:
    snapshot = get_donation_snapshot(db, donation_id)
    if snapshot is None:
        return {
            "donation_id": donation_id,
            "source": "fallback",
            "summary": "Donation not found.",
            "matches": [],
            "suggested_actions": [],
        }

    fallback = _fallback_explain(snapshot, db)
    prompt = (
        "Explain this donation's current matching outcome for the donor. "
        "Prioritize the best pending offer and explain why it fits, what its "
        "status means, and the next step.\nFACTS (JSON):\n"
        + json.dumps(snapshot, ensure_ascii=False, default=str)
    )

    text = await _generate_explanation(prompt)
    if text:
        return {
            "donation_id": donation_id,
            "source": "gemini",
            "summary": text,
            "matches": fallback["matches"],
            "suggested_actions": fallback["suggested_actions"],
        }
    return {
        "donation_id": donation_id,
        **fallback,
    }


async def explain_recovery(db: Session) -> dict[str, Any]:
    from app.agent.tools import get_recovery_context

    context = get_recovery_context(db)
    needing = context.get("donations_needing_recovery") or []
    lines = []
    if needing:
        lines.append(
            f"{len(needing)} donation(s) need recovery attention; "
            f"{context.get('total_remaining_portions_at_risk', 0)} portions remain at risk."
        )
    else:
        lines.append(
            "No donations are currently flagged for recovery, so no rematch is needed right now."
        )
    for d in needing[:5]:
        reasons = []
        if d["declined_invitations"]:
            reasons.append(f"{d['declined_invitations']} recipient(s) declined")
        if not d["pending_invitations"]:
            reasons.append("no offer is waiting for a response")
        if d["pending_invitations"]:
            reasons.append(
                f"{d['pending_invitations']} offer(s) are still awaiting a response"
            )
        if d["minutes_to_deadline"] <= 0:
            urgency = "the pickup deadline has passed or is due"
        elif d["minutes_to_deadline"] <= 60:
            urgency = f"about {d['minutes_to_deadline']} minutes remain before pickup deadline"
        else:
            urgency = "the pickup deadline is still ahead"
        lines.append(
            f"Donation #{d['donation_id']} from {d['donor_name']} has "
            f"{d['remaining_portions']} portions left; "
            f"{'; '.join(reasons)}. {urgency}."
        )

    fallback_summary = " ".join(lines)
    facts = {
        "donations_needing_recovery": needing[:5],
        "count": context.get("count", 0),
        "total_remaining_portions_at_risk": context.get(
            "total_remaining_portions_at_risk", 0
        ),
    }
    prompt = (
        "Explain the current recovery queue for an administrator. State the "
        "scale of the issue, why the listed donations need action, and what "
        "to do next. If the queue is empty, explain that clearly.\nFACTS (JSON):\n"
        + json.dumps(facts, ensure_ascii=False, default=str)
    )
    text = await _generate_explanation(prompt)
    return {
        "source": "gemini" if text else "fallback",
        "summary": text or fallback_summary,
        "context": context,
    }
