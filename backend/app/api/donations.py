from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, require_roles
from app.db.models import Donation, Invitation
from app.db.session import get_db
from app.schemas import DonationCreate, DonationOut
from app.services.audit import record_event
from app.services.matching import create_invitations, explain_matches

router = APIRouter(prefix="/donations", tags=["donations"])


def _serialize(d: Donation) -> dict:
    return {
        "id": d.id,
        "donor_name": d.donor_name,
        "category": d.category,
        "food_name": d.food_name,
        "total_portions": d.total_portions,
        "remaining_portions": d.remaining_portions,
        "pickup_deadline": d.pickup_deadline,
        "pickup_address": d.pickup_address,
        "notes": d.notes,
        "status": d.status,
        "is_demo": d.is_demo,
        "created_at": d.created_at,
    }


@router.post("", status_code=201)
def create_donation(
    payload: DonationCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("donor", "admin")),
):
    deadline = payload.pickup_deadline
    if deadline.tzinfo is None:
        raise HTTPException(
            422, "pickup_deadline must include a timezone (e.g. ...Z or +00:00)"
        )
    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(422, "Pickup deadline must be in the future")
    if payload.total_portions <= 0:
        raise HTTPException(422, "total_portions must be greater than zero")

    donation = Donation(
        donor_name=payload.donor_name,
        category=payload.category.lower().strip(),
        food_name=payload.food_name,
        total_portions=payload.total_portions,
        remaining_portions=payload.total_portions,
        pickup_deadline=deadline,
        pickup_address=payload.pickup_address,
        notes=payload.notes,
        status="open",
        is_demo=payload.is_demo or user.auth_method == "demo",
        organization_id=user.organization_id,
    )
    db.add(donation)
    db.flush()

    invitations = create_invitations(db, donation)
    record_event(
        db,
        entity_type="donation",
        entity_id=donation.id,
        action="donation_created",
        actor_role=user.role,
        actor_id=user.uid,
        details={
            "total_portions": donation.total_portions,
            "invitations": len(invitations),
        },
    )
    db.commit()
    db.refresh(donation)

    return {
        **_serialize(donation),
        "invitations_created": len(invitations),
    }


@router.get("")
def list_donations(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
):
    q = db.query(Donation).order_by(Donation.id.desc())
    if user.role == "donor" and user.organization_id:
        q = q.filter(Donation.organization_id == user.organization_id)
    rows = q.limit(limit).all()
    return [_serialize(d) for d in rows]


@router.get("/{donation_id}")
def get_donation(
    donation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(404, "Donation not found")
    if (
        user.role == "donor"
        and user.organization_id
        and donation.organization_id
        and donation.organization_id != user.organization_id
    ):
        raise HTTPException(403, "Not authorized for this donation")
    return _serialize(donation)


@router.get("/{donation_id}/matches")
def get_matches(
    donation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
):
    donation = db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(404, "Donation not found")
    invitations = (
        db.query(Invitation)
        .filter(Invitation.donation_id == donation_id)
        .order_by(Invitation.score.desc(), Invitation.id.asc())
        .all()
    )
    return explain_matches(donation, invitations)
