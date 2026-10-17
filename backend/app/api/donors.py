from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import AuthUser, require_roles
from app.db.models import Donation
from app.db.session import get_db

router = APIRouter(prefix="/donors", tags=["donors"])


@router.get("/me/donations")
def my_donations(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("donor", "admin")),
):
    q = db.query(Donation).order_by(Donation.id.desc())
    if user.role == "donor" and user.organization_id:
        q = q.filter(Donation.organization_id == user.organization_id)
    return [
        {
            "id": d.id,
            "donor_name": d.donor_name,
            "category": d.category,
            "total_portions": d.total_portions,
            "remaining_portions": d.remaining_portions,
            "status": d.status,
            "is_demo": d.is_demo,
            "pickup_deadline": d.pickup_deadline.isoformat()
            if d.pickup_deadline
            else None,
        }
        for d in q.limit(100).all()
    ]
