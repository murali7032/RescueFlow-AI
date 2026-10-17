"""Gemini / ADK-compatible explanation agent with deterministic fallback.

The model never allocates portions or mutates the database. It only
explains rankings and suggests recovery actions from provided snapshots.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.agent.tools import get_donation_snapshot, get_recipient_name
from app.config import get_settings

logger = logging.getLogger(__name__)


def _fallback_explain(snapshot: dict, db: Session) -> dict[str, Any]:
    matches = snapshot.get("matches") or []
    donation = snapshot["donation"]
    lines = [
        f"Donation #{donation['id']} from {donation['donor_name']}: "
        f"{donation['remaining_portions']}/{donation['total_portions']} "
        f"{donation['category']} portions remain (status: {donation['status']})."
    ]
    pending = [m for m in matches if m.get("status") == "pending"]
    declined = [m for m in matches if m.get("status") == "declined"]
    accepted = [m for m in matches if m.get("status") == "accepted"]

    if pending:
        lines.append("Ranked pending offers (deterministic scores):")
        for m in pending[:5]:
            name = get_recipient_name(db, m["recipient_id"])
            reasons = "; ".join((m.get("reasons") or [])[:2])
            lines.append(
                f"- {name}: score {m['score']}, offer {m['suggested_portions']} "
                f"portions. {reasons}"
            )
    if declined:
        lines.append(
            f"{len(declined)} decline(s) recorded — stock was not reduced; "
            "recovery rematching fills remaining capacity."
        )
    if accepted:
        lines.append(
            f"{len(accepted)} acceptance(s) allocated; pickup remains separate "
            "until explicitly confirmed."
        )

    actions: list[str] = []
    if donation["remaining_portions"] > 0 and not pending:
        actions.append("Trigger recovery rematch for remaining portions")
    if pending:
        actions.append("Wait for recipient responses or follow up on top-ranked offer")
    if declined:
        actions.append("Review declined recipients; default policy blocks auto re-invite")
    if not actions:
        actions.append("Monitor pickup confirmation for allocated portions")

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
                    temperature=0.2,
                    max_output_tokens=512,
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
        "You are RescueFlow AI explaining surplus-food recovery decisions. "
        "Use ONLY the JSON facts below. Do not invent recipients, pickups, "
        "or impact metrics. Do not allocate food. Be concise (under 180 words).\n\n"
        f"FACTS:\n{snapshot}\n\n"
        "Explain why recipients were ranked, note any declines/recovery, "
        "and suggest next operational steps."
    )

    text = await _call_gemini(prompt)
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
    if not needing:
        summary = "No donations currently need recovery. All open surplus has pending offers or is fully allocated."
        return {"source": "fallback", "summary": summary, "context": context}

    lines = [
        f"{len(needing)} donation(s) need recovery attention; "
        f"{context.get('total_remaining_portions_at_risk', 0)} portions remain at risk."
    ]
    for d in needing[:5]:
        lines.append(
            f"Donation #{d['donation_id']} ({d['donor_name']}): "
            f"{d['remaining_portions']} remaining, "
            f"{d['declined_invitations']} declines, "
            f"{d['pending_invitations']} pending."
        )

    fallback_summary = " ".join(lines)
    prompt = (
        "Summarize surplus-food recovery status for an admin. "
        "Use ONLY these facts. Do not invent metrics.\n"
        f"{context}"
    )
    text = await _call_gemini(prompt)
    return {
        "source": "gemini" if text else "fallback",
        "summary": text or fallback_summary,
        "context": context,
    }
