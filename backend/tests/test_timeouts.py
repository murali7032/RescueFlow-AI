from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.models import Allocation, Donation, Invitation
from app.services.allocations import accept_invitation
from app.services.matching import create_invitations
from app.services.timeouts import run_timeout_sweep


def _setup_donation(db_session, seed_recipients, portions=120):
    donation = Donation(
        donor_name="Harbor Bistro",
        category="vegetarian",
        food_name="Veg thali",
        total_portions=portions,
        remaining_portions=portions,
        pickup_deadline=datetime.now(timezone.utc) + timedelta(hours=2),
        status="open",
        is_demo=True,
    )
    db_session.add(donation)
    db_session.commit()
    create_invitations(db_session, donation)
    db_session.commit()
    return donation


def _pending(db_session, donation_id):
    return (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation_id,
            Invitation.status == "pending",
        )
        .order_by(Invitation.id.asc())
        .all()
    )


def test_response_timeout_expires_offer_and_rematches(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    first = _pending(db_session, donation.id)[0]
    first_recipient_id = first.recipient_id
    now = datetime.now(timezone.utc)
    first.expires_at = now - timedelta(seconds=1)
    db_session.commit()

    result = run_timeout_sweep(db_session, now=now)

    db_session.refresh(donation)
    db_session.refresh(first)
    assert result["expired_invitations"] == 1
    assert result["rematched_donations"] == 1
    assert first.status == "expired"
    assert first.responded_at is not None
    assert donation.status == "invited"
    pending = _pending(db_session, donation.id)
    assert all(inv.recipient_id != first_recipient_id for inv in pending)
    assert sum(inv.suggested_portions for inv in pending) <= donation.remaining_portions


def test_pickup_deadline_expires_all_offers_without_rematching(
    db_session, seed_recipients
):
    donation = _setup_donation(db_session, seed_recipients)
    now = datetime.now(timezone.utc)
    donation.pickup_deadline = now - timedelta(seconds=1)
    for invitation in _pending(db_session, donation.id):
        invitation.expires_at = now + timedelta(minutes=10)
    db_session.commit()

    result = run_timeout_sweep(db_session, now=now)

    db_session.refresh(donation)
    assert donation.status == "expired"
    assert result["expired_donations"] == 1
    assert result["rematched_donations"] == 0
    assert all(inv.status == "expired" for inv in _pending_including_expired(db_session, donation.id))


def _pending_including_expired(db_session, donation_id):
    return (
        db_session.query(Invitation)
        .filter(Invitation.donation_id == donation_id)
        .all()
    )


def test_repeat_sweep_is_idempotent(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    now = datetime.now(timezone.utc)
    first = _pending(db_session, donation.id)[0]
    first.expires_at = now - timedelta(seconds=1)
    db_session.commit()

    run_timeout_sweep(db_session, now=now)
    second = run_timeout_sweep(db_session, now=now)

    assert second["expired_invitations"] == 0
    assert second["rematched_donations"] == 0
    assert len(_pending(db_session, donation.id)) >= 1


def test_accept_rejects_expired_invitation_and_rematches(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    first = _pending(db_session, donation.id)[0]
    now = datetime.now(timezone.utc)
    first.expires_at = now - timedelta(seconds=1)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        accept_invitation(db_session, first.id)

    assert exc.value.status_code == 409
    db_session.refresh(first)
    db_session.refresh(donation)
    assert first.status == "expired"
    assert donation.remaining_portions == donation.total_portions
    assert db_session.query(Allocation).filter_by(donation_id=donation.id).count() == 0
