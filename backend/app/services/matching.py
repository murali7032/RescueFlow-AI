"""Deterministic eligibility filtering and ranking for RescueFlow AI.

Hard constraints are applied before scoring. Generative models must never
override these filters. Distance values are synthetic demo estimates, not
live routing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Donation, Invitation, Recipient
from app.services.audit import record_event


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _score_recipient(
    donation: Donation,
    recipient: Recipient,
    now: datetime,
) -> tuple[int, dict, list[str]]:
    settings = get_settings()
    deadline = as_utc(donation.pickup_deadline)
    pickup = as_utc(recipient.earliest_pickup)

    total_window = max((deadline - now).total_seconds(), 1)
    time_left_after_pickup = max((deadline - pickup).total_seconds(), 0)

    deadline_score = time_left_after_pickup / total_window
    capacity_score = min(
        recipient.available_capacity / max(donation.remaining_portions, 1),
        1.0,
    )
    distance_score = 1 / (1 + max(float(recipient.distance_km), 0.0))
    preference_score = (
        1.0
        if donation.category in (recipient.preferred_categories or [])
        else 0.5
    )

    breakdown = {
        "deadline": round(deadline_score, 4),
        "capacity": round(capacity_score, 4),
        "distance": round(distance_score, 4),
        "preference": round(preference_score, 4),
        "weights": {
            "deadline": settings.weight_deadline,
            "capacity": settings.weight_capacity,
            "distance": settings.weight_distance,
            "preference": settings.weight_preference,
        },
        "distance_note": "Synthetic demo distance (not live traffic)",
    }

    score = round(
        100
        * (
            settings.weight_deadline * deadline_score
            + settings.weight_capacity * capacity_score
            + settings.weight_distance * distance_score
            + settings.weight_preference * preference_score
        )
    )

    reasons: list[str] = []
    if preference_score >= 1.0:
        reasons.append(f"Prefers {donation.category} meals")
    reasons.append(
        f"Can collect by {pickup.isoformat()} before deadline {deadline.isoformat()}"
    )
    reasons.append(f"Capacity {recipient.available_capacity} portions available")
    reasons.append(
        f"Synthetic distance ~{recipient.distance_km} km from pickup"
    )

    return score, breakdown, reasons


def is_eligible(
    donation: Donation,
    recipient: Recipient,
    now: datetime | None = None,
    *,
    exclude_statuses: set[str] | None = None,
    prior_invitation: Invitation | None = None,
) -> tuple[bool, str]:
    """Return (eligible, reason_if_not)."""
    now = now or datetime.now(timezone.utc)
    deadline = as_utc(donation.pickup_deadline)

    if donation.status not in {"open", "invited", "no_match", "partially_allocated"}:
        return False, f"Donation status is {donation.status}"
    if donation.remaining_portions <= 0:
        return False, "No remaining portions"
    if deadline <= now:
        return False, "Donation deadline has passed"
    if not recipient.active:
        return False, "Recipient is inactive"
    if recipient.available_capacity <= 0:
        return False, "Recipient has no capacity"
    if donation.category not in (recipient.accepted_categories or []):
        return False, "Food category not accepted"

    pickup = as_utc(recipient.earliest_pickup)
    if pickup < now:
        return False, "Earliest pickup is in the past"
    if pickup > deadline:
        return False, "Cannot collect before donation deadline"

    if prior_invitation and prior_invitation.status in (
        exclude_statuses
        or {"accepted", "declined", "cancelled"}
    ):
        # Declined recipients are not re-invited unless retry policy allows.
        # Default retry policy: no automatic re-invite after decline/accept/cancel.
        return False, f"Prior invitation status is {prior_invitation.status}"

    return True, "eligible"


def rank_recipients(
    donation: Donation,
    recipients: list[Recipient],
    invitations_by_recipient: dict[int, Invitation],
    now: datetime | None = None,
) -> list[dict]:
    """Filter ineligible, score eligible, return deterministic ranked list."""
    now = now or datetime.now(timezone.utc)
    ranked: list[tuple[int, int, dict]] = []

    for recipient in recipients:
        prior = invitations_by_recipient.get(recipient.id)
        ok, reason = is_eligible(
            donation, recipient, now, prior_invitation=prior
        )
        if not ok:
            continue
        score, breakdown, reasons = _score_recipient(donation, recipient, now)
        ranked.append(
            (
                score,
                recipient.id,  # tie-break for determinism
                {
                    "recipient": recipient,
                    "score": score,
                    "breakdown": breakdown,
                    "reasons": reasons,
                    "prior_invitation": prior,
                },
            )
        )

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked]


def create_invitations(db: Session, donation: Donation) -> list[Invitation]:
    """
    Rebalance pending invitations against current remaining stock.

    Lifecycle states set here (per diagram):
    - MATCHING  — entered while the algorithm is running
    - INVITED   — set when >= 1 pending invitation exists after matching
    - NO_MATCH  — set when 0 eligible recipients are found

    Policy:
    - Suggested quantities across pending offers never exceed remaining stock.
    - Offers are suggestions, not reservations.
    - Recipients who accepted/declined/cancelled are not re-invited (no retry).
    - Pending offers for recipients who receive no stock in this pass are cancelled.
    """
    now = datetime.now(timezone.utc)

    if donation.status not in {"open", "partially_allocated", "no_match", "invited"}:
        return []
    if donation.remaining_portions <= 0:
        return []
    if as_utc(donation.pickup_deadline) <= now:
        donation.status = "expired"
        return []

    # Diagram: enter MATCHING while the algorithm runs
    prev_status = donation.status
    donation.status = "matching"
    db.flush()

    invitations = (
        db.query(Invitation).filter(Invitation.donation_id == donation.id).all()
    )
    by_recipient = {inv.recipient_id: inv for inv in invitations}

    recipients = db.query(Recipient).filter(Recipient.active.is_(True)).all()
    ranked = rank_recipients(donation, recipients, by_recipient, now)

    unassigned = donation.remaining_portions
    created: list[Invitation] = []
    assigned_recipient_ids: set[int] = set()

    for entry in ranked:
        if unassigned <= 0:
            break

        recipient: Recipient = entry["recipient"]
        portions = min(unassigned, recipient.available_capacity)
        if portions <= 0:
            continue

        invitation: Invitation | None = entry["prior_invitation"]
        if invitation is None:
            invitation = Invitation(
                donation_id=donation.id,
                recipient_id=recipient.id,
                suggested_portions=portions,
                score=entry["score"],
                score_breakdown=entry["breakdown"],
                reasons=entry["reasons"],
                status="pending",
            )
            db.add(invitation)
            created.append(invitation)
        elif invitation.status == "pending":
            invitation.suggested_portions = portions
            invitation.score = entry["score"]
            invitation.score_breakdown = entry["breakdown"]
            invitation.reasons = entry["reasons"]
        else:
            continue

        assigned_recipient_ids.add(recipient.id)
        unassigned -= portions

    for invitation in invitations:
        if invitation.status != "pending":
            continue
        if invitation.recipient_id not in assigned_recipient_ids:
            invitation.status = "cancelled"

    # Diagram: MATCHING → INVITED (eligible found) or NO_MATCH (none eligible)
    pending_count = len(assigned_recipient_ids)
    if pending_count > 0:
        donation.status = "invited"
    else:
        donation.status = "no_match"

    record_event(
        db,
        entity_type="donation",
        entity_id=donation.id,
        action="invitations_rebalanced",
        details={
            "remaining_portions": donation.remaining_portions,
            "created": len(created),
            "assigned_recipients": list(assigned_recipient_ids),
            "prev_status": prev_status,
            "new_status": donation.status,
        },
    )
    db.flush()
    return created


def explain_matches(donation: Donation, invitations: list[Invitation]) -> list[dict]:
    """Structured match explanation without calling a generative model."""
    results = []
    for inv in sorted(invitations, key=lambda i: (-(i.score or 0), i.id)):
        results.append(
            {
                "invitation_id": inv.id,
                "recipient_id": inv.recipient_id,
                "suggested_portions": inv.suggested_portions,
                "score": inv.score,
                "status": inv.status,
                "breakdown": inv.score_breakdown or {},
                "reasons": inv.reasons or [],
            }
        )
    return results
