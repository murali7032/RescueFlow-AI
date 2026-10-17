"""Transaction-safe allocation and invitation response handling.

Stale-offer policy: on accept, allocate min(suggested, remaining, capacity).
If that amount is > 0, accept succeeds with possibly reduced portions.
If 0, return 409 conflict requiring a refreshed offer.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import Allocation, Donation, Invitation, Recipient
from app.services.audit import record_event
from app.services.matching import create_invitations


def _sync_donation_status(donation: Donation) -> None:
    if donation.remaining_portions <= 0:
        donation.status = "allocated"
        donation.remaining_portions = 0
    elif donation.remaining_portions < donation.total_portions:
        donation.status = "partially_allocated"
    else:
        donation.status = "open"


def accept_invitation(
    db: Session,
    invitation_id: int,
    *,
    actor_role: str | None = None,
    actor_id: str | None = None,
) -> Allocation:
    """Accept invitation and reserve portions under row locks when supported."""
    try:
        invitation = (
            db.query(Invitation)
            .filter(Invitation.id == invitation_id)
            .with_for_update()
            .first()
        )
        if invitation is None:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Invitation is already {invitation.status}",
            )

        donation = (
            db.query(Donation)
            .filter(Donation.id == invitation.donation_id)
            .with_for_update()
            .first()
        )
        recipient = (
            db.query(Recipient)
            .filter(Recipient.id == invitation.recipient_id)
            .with_for_update()
            .first()
        )

        if donation is None or recipient is None:
            raise HTTPException(
                status_code=404, detail="Donation or recipient not found"
            )

        if donation.status not in {"open", "partially_allocated"}:
            raise HTTPException(
                status_code=409, detail="Donation is no longer open for allocation"
            )

        now = datetime.now(timezone.utc)
        deadline = donation.pickup_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline <= now:
            invitation.status = "expired"
            donation.status = "expired"
            db.commit()
            raise HTTPException(status_code=409, detail="Donation deadline has passed")

        if donation.remaining_portions <= 0:
            raise HTTPException(status_code=409, detail="No portions remain")

        if not recipient.active:
            raise HTTPException(status_code=409, detail="Recipient is inactive")

        portions = min(
            invitation.suggested_portions,
            donation.remaining_portions,
            recipient.available_capacity,
        )
        if portions <= 0:
            raise HTTPException(
                status_code=409,
                detail="Offer is stale; no portions or capacity available. Refresh offers.",
            )

        donation.remaining_portions -= portions
        recipient.available_capacity -= portions
        if recipient.available_capacity < 0:
            raise HTTPException(
                status_code=409, detail="Capacity would become negative"
            )

        invitation.status = "accepted"
        invitation.responded_at = now

        allocation = Allocation(
            donation_id=donation.id,
            recipient_id=recipient.id,
            invitation_id=invitation.id,
            portions=portions,
            pickup_status="pending",
        )
        db.add(allocation)

        _sync_donation_status(donation)

        if donation.remaining_portions == 0:
            (
                db.query(Invitation)
                .filter(
                    Invitation.donation_id == donation.id,
                    Invitation.id != invitation.id,
                    Invitation.status == "pending",
                )
                .update({"status": "cancelled"}, synchronize_session=False)
            )
        else:
            # Rebalance remaining pending offers to current stock.
            create_invitations(db, donation)

        record_event(
            db,
            entity_type="allocation",
            entity_id="pending",
            action="invitation_accepted",
            actor_role=actor_role,
            actor_id=actor_id,
            details={
                "invitation_id": invitation.id,
                "donation_id": donation.id,
                "recipient_id": recipient.id,
                "portions": portions,
                "suggested_portions": invitation.suggested_portions,
                "remaining_portions": donation.remaining_portions,
            },
        )

        db.commit()
        db.refresh(allocation)

        # Fix audit entity id after commit
        record_event(
            db,
            entity_type="allocation",
            entity_id=allocation.id,
            action="allocation_created",
            actor_role=actor_role,
            actor_id=actor_id,
            details={"portions": portions, "pickup_status": "pending"},
        )
        db.commit()

        return allocation

    except Exception:
        db.rollback()
        raise


def decline_invitation(
    db: Session,
    invitation_id: int,
    *,
    actor_role: str | None = None,
    actor_id: str | None = None,
    rematch: bool = True,
) -> tuple[Invitation, list[Invitation]]:
    """Decline without reducing stock or capacity; optionally rematch."""
    try:
        invitation = (
            db.query(Invitation)
            .filter(Invitation.id == invitation_id)
            .with_for_update()
            .first()
        )
        if invitation is None:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Invitation is already {invitation.status}",
            )

        invitation.status = "declined"
        invitation.responded_at = datetime.now(timezone.utc)

        record_event(
            db,
            entity_type="invitation",
            entity_id=invitation.id,
            action="invitation_declined",
            actor_role=actor_role,
            actor_id=actor_id,
            details={
                "donation_id": invitation.donation_id,
                "recipient_id": invitation.recipient_id,
            },
        )

        new_invitations: list[Invitation] = []
        donation = db.get(Donation, invitation.donation_id)
        if rematch and donation is not None:
            new_invitations = create_invitations(db, donation)
            record_event(
                db,
                entity_type="donation",
                entity_id=donation.id,
                action="recovery_rematch_after_decline",
                details={"new_invitations": len(new_invitations)},
            )

        db.commit()
        db.refresh(invitation)
        return invitation, new_invitations

    except Exception:
        db.rollback()
        raise


def update_pickup_status(
    db: Session,
    allocation_id: int,
    new_status: str,
    *,
    actor_role: str | None = None,
    actor_id: str | None = None,
) -> Allocation:
    allowed = {"pending", "confirmed", "completed", "failed"}
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid pickup status: {new_status}")

    allocation = db.get(Allocation, allocation_id)
    if allocation is None:
        raise HTTPException(status_code=404, detail="Allocation not found")

    now = datetime.now(timezone.utc)
    allocation.pickup_status = new_status
    if new_status == "confirmed":
        allocation.pickup_confirmed_at = now
    if new_status == "completed":
        allocation.pickup_completed_at = now

    record_event(
        db,
        entity_type="allocation",
        entity_id=allocation.id,
        action="pickup_status_updated",
        actor_role=actor_role,
        actor_id=actor_id,
        details={"pickup_status": new_status},
    )
    db.commit()
    db.refresh(allocation)
    return allocation
