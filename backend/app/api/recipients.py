from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, require_roles
from app.db.models import Recipient
from app.db.session import get_db
from app.services.invitations import list_for_recipient

router = APIRouter(prefix="/recipients", tags=["recipients"])


def _serialize(r: Recipient) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "available_capacity": r.available_capacity,
        "max_capacity": r.max_capacity,
        "accepted_categories": r.accepted_categories,
        "preferred_categories": r.preferred_categories,
        "distance_km": r.distance_km,
        "distance_note": "Synthetic demo distance (not live traffic)",
        "earliest_pickup": r.earliest_pickup.isoformat() if r.earliest_pickup else None,
        "active": r.active,
        "is_demo": r.is_demo,
    }


@router.get("")
def list_recipients(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin", "donor")),
    active_only: bool = Query(True),
):
    q = db.query(Recipient)
    if active_only:
        q = q.filter(Recipient.active.is_(True))
    return [_serialize(r) for r in q.order_by(Recipient.id.asc()).all()]


@router.get("/me/invitations")
def my_invitations(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin")),
    recipient_id: int | None = Query(
        None, description="Required for admin/demo when not bound to a recipient"
    ),
):
    rid = user.recipient_id or recipient_id
    if rid is None:
        raise HTTPException(
            400,
            "recipient_id required (set X-Demo-Recipient-Id or pass ?recipient_id=)",
        )
    return list_for_recipient(db, rid)


@router.get("/{recipient_id}")
def get_recipient(
    recipient_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    if user.role == "recipient" and user.recipient_id not in (None, recipient_id):
        raise HTTPException(403, "Not authorized for this recipient")
    r = db.get(Recipient, recipient_id)
    if r is None:
        raise HTTPException(404, "Recipient not found")
    return _serialize(r)
