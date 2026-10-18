"""Expire unanswered invitations and rematch stock that can still be collected."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Donation, Invitation
from app.services.audit import record_event
from app.services.matching import as_utc, create_invitations

_ACTIVE_DONATION_STATUSES = (
    "open",
    "matching",
    "invited",
    "no_match",
    "partially_allocated",
)


def process_donation_timeouts(
    db: Session, donation: Donation, *, now: datetime | None = None
) -> dict[str, int | bool]:
    """Expire a donation's due offers, rematching only before its pickup deadline.

    The caller must hold a row lock on ``donation``. Invitations are then locked
    in ID order to serialize with accept and decline operations.
    """
    now = as_utc(now or datetime.now(timezone.utc))
    pending = (
        db.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .order_by(Invitation.id.asc())
        .with_for_update()
        .all()
    )
    deadline_passed = as_utc(donation.pickup_deadline) <= now
    due = pending if deadline_passed else [
        invitation
        for invitation in pending
        if as_utc(invitation.expires_at) <= now
    ]

    for invitation in due:
        invitation.status = "expired"
        invitation.responded_at = now
        record_event(
            db,
            entity_type="invitation",
            entity_id=invitation.id,
            action="invitation_expired",
            details={
                "donation_id": donation.id,
                "recipient_id": invitation.recipient_id,
                "reason": "pickup_deadline" if deadline_passed else "response_timeout",
            },
        )

    if deadline_passed:
        if donation.remaining_portions > 0:
            donation.status = "expired"
        elif donation.status not in {"allocated", "completed"}:
            donation.status = "allocated"
        if donation.remaining_portions > 0:
            record_event(
                db,
                entity_type="donation",
                entity_id=donation.id,
                action="donation_expired",
                details={"remaining_portions": donation.remaining_portions},
            )
        return {
            "processed": bool(due) or donation.remaining_portions > 0,
            "expired_invitations": len(due),
            "rematched_donations": 0,
            "new_invitations": 0,
            "expired_donations": int(donation.remaining_portions > 0),
        }

    if not due:
        return {
            "processed": False,
            "expired_invitations": 0,
            "rematched_donations": 0,
            "new_invitations": 0,
            "expired_donations": 0,
        }

    # Flush timeout statuses before the matcher reads prior invitations.
    db.flush()
    created = create_invitations(db, donation) if donation.remaining_portions > 0 else []
    record_event(
        db,
        entity_type="donation",
        entity_id=donation.id,
        action="recovery_rematch_after_timeout",
        details={
            "expired_invitations": len(due),
            "new_invitations": len(created),
            "remaining_portions": donation.remaining_portions,
        },
    )
    return {
        "processed": True,
        "expired_invitations": len(due),
        "rematched_donations": 1,
        "new_invitations": len(created),
        "expired_donations": 0,
    }


def run_timeout_sweep(
    db: Session,
    *,
    now: datetime | None = None,
    batch_size: int = 100,
) -> dict[str, int]:
    """Process a bounded batch of response timeouts and pickup deadlines."""
    now = as_utc(now or datetime.now(timezone.utc))
    deadline_ids = (
        db.query(Donation.id)
        .filter(
            Donation.status.in_(_ACTIVE_DONATION_STATUSES),
            Donation.remaining_portions > 0,
            Donation.pickup_deadline <= now,
        )
        .order_by(Donation.id.asc())
        .limit(batch_size)
        .all()
    )
    expired_with_pending_ids = (
        db.query(Donation.id)
        .join(Invitation, Invitation.donation_id == Donation.id)
        .filter(
            Donation.status == "expired",
            Donation.remaining_portions > 0,
            Donation.pickup_deadline <= now,
            Invitation.status == "pending",
        )
        .distinct()
        .order_by(Donation.id.asc())
        .limit(batch_size)
        .all()
    )
    timeout_ids = (
        db.query(Invitation.donation_id)
        .join(Donation, Donation.id == Invitation.donation_id)
        .filter(
            Invitation.status == "pending",
            Invitation.expires_at <= now,
            Donation.status.in_(_ACTIVE_DONATION_STATUSES),
            Donation.remaining_portions > 0,
        )
        .order_by(Invitation.donation_id.asc())
        .limit(batch_size)
        .all()
    )
    donation_ids = sorted(
        {row[0] for row in deadline_ids + expired_with_pending_ids + timeout_ids}
    )[:batch_size]

    totals = {
        "donations_examined": 0,
        "expired_invitations": 0,
        "rematched_donations": 0,
        "new_invitations": 0,
        "expired_donations": 0,
        "skipped_locked": 0,
    }

    for donation_id in donation_ids:
        donation = (
            db.query(Donation)
            .filter(Donation.id == donation_id)
            .with_for_update(skip_locked=True)
            .first()
        )
        if donation is None:
            totals["skipped_locked"] += 1
            continue

        try:
            result = process_donation_timeouts(db, donation, now=now)
            db.commit()
        except Exception:
            db.rollback()
            raise

        if result["processed"]:
            totals["donations_examined"] += 1
            for key in (
                "expired_invitations",
                "rematched_donations",
                "new_invitations",
                "expired_donations",
            ):
                totals[key] += int(result[key])

    return totals
