from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import AuthUser, require_roles
from app.db.models import Allocation, AuditEvent, Donation, DonationReview, Invitation
from app.db.session import get_db
from app.services.recovery import recovery_summary, run_recovery

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    total_donations = db.query(func.count(Donation.id)).scalar() or 0
    total_portions = (
        db.query(func.coalesce(func.sum(Donation.total_portions), 0)).scalar() or 0
    )
    remaining = (
        db.query(func.coalesce(func.sum(Donation.remaining_portions), 0)).scalar()
        or 0
    )
    allocated_portions = (
        db.query(func.coalesce(func.sum(Allocation.portions), 0)).scalar() or 0
    )
    confirmed_pickups = (
        db.query(func.coalesce(func.sum(Allocation.portions), 0))
        .filter(Allocation.pickup_status.in_(["confirmed", "completed"]))
        .scalar()
        or 0
    )
    completed_pickups = (
        db.query(func.coalesce(func.sum(Allocation.portions), 0))
        .filter(Allocation.pickup_status == "completed")
        .scalar()
        or 0
    )
    pending_invites = (
        db.query(func.count(Invitation.id))
        .filter(Invitation.status == "pending")
        .scalar()
        or 0
    )
    declined_invites = (
        db.query(func.count(Invitation.id))
        .filter(Invitation.status == "declined")
        .scalar()
        or 0
    )
    recovery = recovery_summary(db)
    recovery_rate = 0.0
    if total_portions:
        recovery_rate = round(100 * float(allocated_portions) / float(total_portions), 1)

    deadline_ok = (
        db.query(func.count(Donation.id))
        .filter(Donation.status.in_(["allocated", "partially_allocated", "open", "invited", "no_match", "matching"]))
        .scalar()
        or 0
    )

    return {
        "label": "Metrics from persisted database records (demo data flagged per row)",
        "total_donations": total_donations,
        "total_portions_donated": int(total_portions),
        "portions_remaining": int(remaining),
        "portions_allocated": int(allocated_portions),
        "portions_pickup_confirmed": int(confirmed_pickups),
        "portions_pickup_completed": int(completed_pickups),
        "pending_invitations": pending_invites,
        "declined_invitations": declined_invites,
        "donations_needing_recovery": recovery["count"],
        "recovery_rate_percent": recovery_rate,
        "deadline_active_donations": deadline_ok,
        "note": "Allocated portions are not meals served until pickup is completed",
    }


@router.get("/recovery")
def recovery(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    return recovery_summary(db)


@router.post("/recovery/{donation_id}")
def trigger_recovery(
    donation_id: int,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    return run_recovery(db, donation_id)


@router.get("/audit-events")
def audit_events(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
    limit: int = Query(50, ge=1, le=200),
):
    rows = (
        db.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "actor_role": e.actor_role,
            "actor_id": e.actor_id,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "action": e.action,
            "details": e.details,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


@router.get("/donor-reviews")
def donor_reviews(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
    limit: int = Query(50, ge=1, le=200),
):
    rows = db.query(DonationReview).order_by(DonationReview.created_at.desc()).limit(limit).all()
    return [
        {
            "id": review.id,
            "donor_name": review.donor_name,
            "donation_id": review.donation_id,
            "food_name": review.donation.food_name if review.donation else None,
            "recipient_name": review.recipient.name if review.recipient else None,
            "rating": review.rating,
            "feedback": review.feedback,
            "created_at": review.created_at.isoformat() if review.created_at else None,
        }
        for review in rows
    ]
