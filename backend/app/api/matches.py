"""Match-related helpers (also covered under donations/{id}/matches)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user
from app.db.models import Donation, Invitation
from app.db.session import get_db
from app.services.matching import create_invitations, explain_matches

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("/{donation_id}/refresh")
def refresh_matches(
    donation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    if user.role not in {"donor", "admin"}:
        raise HTTPException(403, "Donor or admin required")
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(404, "Donation not found")
    created = create_invitations(db, donation)
    db.commit()
    invitations = (
        db.query(Invitation).filter(Invitation.donation_id == donation_id).all()
    )
    return {
        "created": len(created),
        "matches": explain_matches(donation, invitations),
    }
