from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import AuthUser, get_current_user, require_roles
from app.db.models import Allocation, Donation, DonationReview, Recipient
from app.db.session import get_db
from app.schemas import DonationReviewCreate, PickupUpdate
from app.services.allocations import update_pickup_status

router = APIRouter(prefix="/allocations", tags=["allocations"])


def _serialize(a: Allocation, db: Session) -> dict:
    recipient = db.get(Recipient, a.recipient_id)
    donation = db.get(Donation, a.donation_id)
    return {
        "id": a.id,
        "donation_id": a.donation_id,
        "recipient_id": a.recipient_id,
        "recipient_name": recipient.name if recipient else None,
        "donor_name": donation.donor_name if donation else None,
        "food_name": donation.food_name if donation else None,
        "invitation_id": a.invitation_id,
        "portions": a.portions,
        "pickup_status": a.pickup_status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "pickup_confirmed_at": a.pickup_confirmed_at.isoformat()
        if a.pickup_confirmed_at
        else None,
        "pickup_completed_at": a.pickup_completed_at.isoformat()
        if a.pickup_completed_at
        else None,
        "reviewed": db.query(DonationReview.id).filter_by(allocation_id=a.id).first() is not None,
    }


@router.get("")
def list_allocations(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
    donation_id: int | None = Query(None),
    recipient_id: int | None = Query(None),
):
    q = db.query(Allocation)
    if donation_id is not None:
        q = q.filter(Allocation.donation_id == donation_id)
    if user.role == "recipient":
        rid = user.recipient_id or recipient_id
        if rid is None:
            raise HTTPException(400, "recipient_id required for recipient role")
        q = q.filter(Allocation.recipient_id == rid)
    elif recipient_id is not None:
        q = q.filter(Allocation.recipient_id == recipient_id)
    rows = q.order_by(Allocation.id.desc()).all()
    return [_serialize(a, db) for a in rows]


@router.patch("/{allocation_id}/pickup")
def patch_pickup(
    allocation_id: int,
    payload: PickupUpdate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin", "donor")),
):
    allocation = update_pickup_status(
        db,
        allocation_id,
        payload.pickup_status,
        actor_role=user.role,
        actor_id=user.uid,
    )
    return _serialize(allocation, db)


@router.post("/{allocation_id}/review")
def review_donation(
    allocation_id: int,
    payload: DonationReviewCreate,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("recipient", "admin")),
):
    allocation = db.get(Allocation, allocation_id)
    if allocation is None:
        raise HTTPException(404, "Allocation not found")
    recipient_id = user.recipient_id
    if user.role == "recipient" and recipient_id != allocation.recipient_id:
        raise HTTPException(403, "You can review only your own completed pickups")
    recipient_id = recipient_id or allocation.recipient_id
    if allocation.pickup_status not in {"confirmed", "completed"}:
        raise HTTPException(409, "Confirm pickup before reviewing this donation")
    if db.query(DonationReview).filter_by(allocation_id=allocation.id).first():
        raise HTTPException(409, "This pickup has already been reviewed")

    donation = db.get(Donation, allocation.donation_id)
    review = DonationReview(
        donation_id=allocation.donation_id,
        allocation_id=allocation.id,
        recipient_id=recipient_id,
        donor_organization_id=donation.organization_id,
        donor_name=donation.donor_name,
        rating=payload.rating,
        feedback=payload.feedback.strip(),
    )
    db.add(review)
    record_event(
        db,
        entity_type="donation",
        entity_id=donation.id,
        action="donor_review_submitted",
        actor_role=user.role,
        actor_id=user.uid,
        details={"rating": payload.rating, "allocation_id": allocation.id},
    )
    db.flush()
    score_query = db.query(
        func.count(DonationReview.id), func.avg(DonationReview.rating)
    )
    if donation.organization_id is not None:
        score_query = score_query.filter(
            DonationReview.donor_organization_id == donation.organization_id
        )
    else:
        score_query = score_query.filter(
            func.lower(DonationReview.donor_name) == donation.donor_name.lower()
        )
    count, average = score_query.one()
    db.commit()
    return {
        "message": "Thank you. Your feedback has been recorded.",
        "donor_score": round(float(average) * 20),
        "review_count": int(count),
        "restricted": count >= 3 and average <= 2,
    }
