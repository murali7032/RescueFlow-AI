"""Read-only tools the AI agent may use. No write/allocate operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Allocation, Donation, Invitation, Recipient
from app.services.matching import explain_matches
from app.services.recovery import recovery_summary


def get_donation_snapshot(db: Session, donation_id: int) -> dict | None:
    donation = db.get(Donation, donation_id)
    if donation is None:
        return None
    invitations = (
        db.query(Invitation).filter(Invitation.donation_id == donation_id).all()
    )
    allocations = (
        db.query(Allocation).filter(Allocation.donation_id == donation_id).all()
    )
    return {
        "donation": {
            "id": donation.id,
            "donor_name": donation.donor_name,
            "category": donation.category,
            "total_portions": donation.total_portions,
            "remaining_portions": donation.remaining_portions,
            "status": donation.status,
            "pickup_deadline": donation.pickup_deadline.isoformat()
            if donation.pickup_deadline
            else None,
        },
        "matches": explain_matches(donation, invitations),
        "allocations": [
            {
                "id": a.id,
                "recipient_id": a.recipient_id,
                "portions": a.portions,
                "pickup_status": a.pickup_status,
            }
            for a in allocations
        ],
    }


def get_recipient_name(db: Session, recipient_id: int) -> str:
    r = db.get(Recipient, recipient_id)
    return r.name if r else f"Recipient {recipient_id}"


def get_recovery_context(db: Session) -> dict:
    return recovery_summary(db)


ALLOWED_TOOL_NAMES = [
    "get_donation_snapshot",
    "get_recovery_context",
]
