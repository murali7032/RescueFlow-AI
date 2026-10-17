"""Invitation query helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Donation, Invitation, Recipient


def serialize_invitation(inv: Invitation, db: Session | None = None) -> dict:
    recipient_name = None
    donation_summary = None
    if db is not None:
        recipient = db.get(Recipient, inv.recipient_id)
        donation = db.get(Donation, inv.donation_id)
        recipient_name = recipient.name if recipient else None
        if donation:
            donation_summary = {
                "id": donation.id,
                "donor_name": donation.donor_name,
                "category": donation.category,
                "food_name": donation.food_name,
                "pickup_deadline": donation.pickup_deadline.isoformat()
                if donation.pickup_deadline
                else None,
                "pickup_address": donation.pickup_address,
                "remaining_portions": donation.remaining_portions,
                "status": donation.status,
            }

    return {
        "id": inv.id,
        "donation_id": inv.donation_id,
        "recipient_id": inv.recipient_id,
        "recipient_name": recipient_name,
        "suggested_portions": inv.suggested_portions,
        "score": inv.score,
        "score_breakdown": inv.score_breakdown,
        "reasons": inv.reasons,
        "status": inv.status,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
        "responded_at": inv.responded_at.isoformat() if inv.responded_at else None,
        "donation": donation_summary,
    }


def list_for_recipient(db: Session, recipient_id: int) -> list[dict]:
    rows = (
        db.query(Invitation)
        .filter(Invitation.recipient_id == recipient_id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    return [serialize_invitation(r, db) for r in rows]


def get_invitation(db: Session, invitation_id: int) -> dict | None:
    inv = db.get(Invitation, invitation_id)
    if inv is None:
        return None
    return serialize_invitation(inv, db)
