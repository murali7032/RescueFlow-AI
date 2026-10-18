"""Recovery lifecycle helpers — rematch remaining surplus after failures."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Allocation, AuditEvent, Donation, Invitation
from app.services.audit import record_event
from app.services.matching import create_invitations


def donations_needing_recovery(db: Session) -> list[dict]:
    """Open/partial donations with remaining stock and recent declines/expiries."""
    now = datetime.now(timezone.utc)
    donations = (
        db.query(Donation)
        .filter(
            Donation.status.in_(["open", "invited", "no_match", "partially_allocated"]),
            Donation.remaining_portions > 0,
        )
        .all()
    )
    results = []
    for donation in donations:
        deadline = donation.pickup_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        declined = (
            db.query(func.count(Invitation.id))
            .filter(
                Invitation.donation_id == donation.id,
                Invitation.status == "declined",
            )
            .scalar()
            or 0
        )
        pending = (
            db.query(func.count(Invitation.id))
            .filter(
                Invitation.donation_id == donation.id,
                Invitation.status == "pending",
            )
            .scalar()
            or 0
        )
        allocated = (
            db.query(func.coalesce(func.sum(Allocation.portions), 0))
            .filter(Allocation.donation_id == donation.id)
            .scalar()
            or 0
        )
        needs_recovery = declined > 0 or pending == 0
        results.append(
            {
                "donation_id": donation.id,
                "donor_name": donation.donor_name,
                "category": donation.category,
                "total_portions": donation.total_portions,
                "remaining_portions": donation.remaining_portions,
                "allocated_portions": int(allocated),
                "status": donation.status,
                "pickup_deadline": deadline.isoformat(),
                "declined_invitations": declined,
                "pending_invitations": pending,
                "needs_recovery": needs_recovery,
                "minutes_to_deadline": max(
                    int((deadline - now).total_seconds() // 60), 0
                ),
                "is_demo": donation.is_demo,
            }
        )
    return results


def run_recovery(db: Session, donation_id: int) -> dict:
    donation = (
        db.query(Donation)
        .filter(Donation.id == donation_id)
        .with_for_update()
        .first()
    )
    if donation is None:
        return {"error": "Donation not found"}

    created = create_invitations(db, donation)
    record_event(
        db,
        entity_type="donation",
        entity_id=donation.id,
        action="manual_recovery_triggered",
        details={"new_invitations": len(created)},
    )
    db.commit()
    return {
        "donation_id": donation.id,
        "remaining_portions": donation.remaining_portions,
        "new_invitations": len(created),
    }


def recovery_summary(db: Session) -> dict:
    donations = donations_needing_recovery(db)
    needing = [d for d in donations if d["needs_recovery"]]
    total_remaining = sum(d["remaining_portions"] for d in needing)
    recent = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.action.in_(
                [
                    "recovery_rematch_after_decline",
                    "manual_recovery_triggered",
                    "invitations_rebalanced",
                ]
            )
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "donations_needing_recovery": needing,
        "count": len(needing),
        "total_remaining_portions_at_risk": total_remaining,
        "recent_recovery_events": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in recent
        ],
    }
