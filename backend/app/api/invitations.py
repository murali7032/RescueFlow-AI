from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser, require_roles
from app.db.session import get_db
from app.services.allocations import accept_invitation, decline_invitation
from app.services.invitations import get_invitation

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("/{invitation_id}")
def read_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin", "donor")),
):
    data = get_invitation(db, invitation_id)
    if data is None:
        raise HTTPException(404, "Invitation not found")
    if (
        user.role == "recipient"
        and user.recipient_id is not None
        and data["recipient_id"] != user.recipient_id
    ):
        raise HTTPException(403, "Not authorized for this invitation")
    return data


@router.post("/{invitation_id}/accept")
def accept(
    invitation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin")),
):
    data = get_invitation(db, invitation_id)
    if data is None:
        raise HTTPException(404, "Invitation not found")
    if (
        user.role == "recipient"
        and user.recipient_id is not None
        and data["recipient_id"] != user.recipient_id
    ):
        raise HTTPException(403, "Not authorized for this invitation")

    allocation = accept_invitation(
        db, invitation_id, actor_role=user.role, actor_id=user.uid
    )
    return {
        "allocation_id": allocation.id,
        "donation_id": allocation.donation_id,
        "recipient_id": allocation.recipient_id,
        "portions": allocation.portions,
        "pickup_status": allocation.pickup_status,
        "note": "Allocation reserved; pickup remains pending until confirmed",
    }


@router.post("/{invitation_id}/decline")
def decline(
    invitation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin")),
):
    data = get_invitation(db, invitation_id)
    if data is None:
        raise HTTPException(404, "Invitation not found")
    if (
        user.role == "recipient"
        and user.recipient_id is not None
        and data["recipient_id"] != user.recipient_id
    ):
        raise HTTPException(403, "Not authorized for this invitation")

    invitation, new_invites = decline_invitation(
        db, invitation_id, actor_role=user.role, actor_id=user.uid, rematch=True
    )
    return {
        "invitation_id": invitation.id,
        "status": invitation.status,
        "new_invitations_created": len(new_invites),
        "note": "Decline recorded; stock unchanged; recovery rematch attempted",
    }
