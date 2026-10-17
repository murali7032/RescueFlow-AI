from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.db.models import Allocation, Donation, Invitation, Recipient
from app.services.allocations import accept_invitation, decline_invitation
from app.services.matching import create_invitations


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


def _pending_for(db_session, donation_id, recipient_id):
    return (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation_id,
            Invitation.recipient_id == recipient_id,
            Invitation.status == "pending",
        )
        .one()
    )


def test_accept_reduces_remaining(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    a = seed_recipients[0]
    inv = _pending_for(db_session, donation.id, a.id)
    allocation = accept_invitation(db_session, inv.id)
    db_session.refresh(donation)
    db_session.refresh(a)
    assert allocation.portions == 80
    assert donation.remaining_portions == 40
    assert donation.status == "partially_allocated"
    assert a.available_capacity == 0
    assert allocation.pickup_status == "pending"


def test_partial_keeps_other_pending(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    a = seed_recipients[0]
    inv_a = _pending_for(db_session, donation.id, a.id)
    accept_invitation(db_session, inv_a.id)
    pending = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .all()
    )
    assert len(pending) >= 1
    assert sum(i.suggested_portions for i in pending) <= 40


def test_full_allocation_cancels_pending(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients, portions=80)
    a = seed_recipients[0]
    inv = _pending_for(db_session, donation.id, a.id)
    accept_invitation(db_session, inv.id)
    db_session.refresh(donation)
    assert donation.remaining_portions == 0
    assert donation.status == "allocated"
    pending = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .count()
    )
    assert pending == 0


def test_decline_does_not_reduce_stock(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    a = seed_recipients[0]
    before_cap = a.available_capacity
    inv = _pending_for(db_session, donation.id, a.id)
    decline_invitation(db_session, inv.id, rematch=True)
    db_session.refresh(donation)
    db_session.refresh(a)
    assert donation.remaining_portions == 120
    assert a.available_capacity == before_cap


def test_rematch_after_decline(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    a = seed_recipients[0]
    inv = _pending_for(db_session, donation.id, a.id)
    _, created = decline_invitation(db_session, inv.id, rematch=True)
    pending = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .all()
    )
    assert all(i.recipient_id != a.id for i in pending)
    assert sum(i.suggested_portions for i in pending) <= 120
    # A should not be re-invited
    reinvited = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.recipient_id == a.id,
            Invitation.status == "pending",
        )
        .count()
    )
    assert reinvited == 0


def test_reject_duplicate_accept(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    inv = _pending_for(db_session, donation.id, seed_recipients[0].id)
    accept_invitation(db_session, inv.id)
    with pytest.raises(HTTPException) as exc:
        accept_invitation(db_session, inv.id)
    assert exc.value.status_code == 409


def test_reject_cancelled_accept(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients, portions=80)
    a_inv = _pending_for(db_session, donation.id, seed_recipients[0].id)
    # Create a second pending then fully allocate via A to cancel others
    others = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
            Invitation.id != a_inv.id,
        )
        .all()
    )
    accept_invitation(db_session, a_inv.id)
    if others:
        with pytest.raises(HTTPException) as exc:
            accept_invitation(db_session, others[0].id)
        assert exc.value.status_code == 409


def test_never_exceed_total(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients, portions=120)
    a = seed_recipients[0]
    accept_invitation(db_session, _pending_for(db_session, donation.id, a.id).id)
    # After rebalance, accept any remaining pending offer
    remaining_invite = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .first()
    )
    assert remaining_invite is not None
    accept_invitation(db_session, remaining_invite.id)
    db_session.refresh(donation)
    total = (
        db_session.query(Allocation)
        .filter(Allocation.donation_id == donation.id)
        .all()
    )
    assert sum(x.portions for x in total) <= 120
    assert donation.remaining_portions >= 0
    assert sum(x.portions for x in total) + donation.remaining_portions == 120


def test_capacity_never_negative(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    a = seed_recipients[0]
    accept_invitation(db_session, _pending_for(db_session, donation.id, a.id).id)
    db_session.refresh(a)
    assert a.available_capacity >= 0


def test_pickup_separate_from_allocation(db_session, seed_recipients):
    donation = _setup_donation(db_session, seed_recipients)
    alloc = accept_invitation(
        db_session, _pending_for(db_session, donation.id, seed_recipients[0].id).id
    )
    assert alloc.pickup_status == "pending"
    assert alloc.pickup_completed_at is None
