from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.models import Donation, Invitation, Recipient
from app.services.matching import create_invitations, is_eligible, rank_recipients


def _donation(portions=120, hours=2, category="vegetarian") -> Donation:
    return Donation(
        donor_name="Harbor Bistro",
        category=category,
        food_name="Veg thali",
        total_portions=portions,
        remaining_portions=portions,
        pickup_deadline=datetime.now(timezone.utc) + timedelta(hours=hours),
        status="open",
        is_demo=True,
    )


def test_exclude_deadline_infeasible(db_session, seed_recipients):
    donation = _donation(hours=2)
    db_session.add(donation)
    db_session.commit()

    d = seed_recipients[3]  # Kitchen D — earliest +3h
    ok, reason = is_eligible(donation, d)
    assert ok is False
    assert "deadline" in reason.lower() or "collect" in reason.lower()


def test_exclude_inactive(db_session, seed_recipients):
    donation = _donation()
    inactive = seed_recipients[4]
    ok, reason = is_eligible(donation, inactive)
    assert ok is False
    assert "inactive" in reason.lower()


def test_rank_deterministic(db_session, seed_recipients):
    donation = _donation()
    db_session.add(donation)
    db_session.commit()

    ranked1 = rank_recipients(donation, seed_recipients, {})
    ranked2 = rank_recipients(donation, seed_recipients, {})
    ids1 = [e["recipient"].id for e in ranked1]
    ids2 = [e["recipient"].id for e in ranked2]
    assert ids1 == ids2
    # D and inactive excluded
    names = [e["recipient"].name for e in ranked1]
    assert "Community Kitchen D" not in names
    assert "Inactive Kitchen" not in names
    assert len(ranked1) == 3


def test_offers_do_not_exceed_stock(db_session, seed_recipients):
    donation = _donation(portions=120)
    db_session.add(donation)
    db_session.commit()

    create_invitations(db_session, donation)
    db_session.commit()

    pending = (
        db_session.query(Invitation)
        .filter(
            Invitation.donation_id == donation.id,
            Invitation.status == "pending",
        )
        .all()
    )
    total = sum(i.suggested_portions for i in pending)
    assert total <= 120
    assert total == 120  # 80+40 from A then B, or similar fill
    assert all(i.suggested_portions > 0 for i in pending)
    # D must not receive an invitation
    d_id = seed_recipients[3].id
    assert all(i.recipient_id != d_id for i in pending)
    assert donation.status == "invited"


def test_matching_status_does_not_block_eligibility(db_session, seed_recipients):
    """Regression: create_invitations sets status=matching before ranking."""
    donation = _donation(portions=120)
    db_session.add(donation)
    db_session.commit()

    # Simulate mid-algorithm status used inside create_invitations.
    donation.status = "matching"
    ok, _ = is_eligible(donation, seed_recipients[0])
    assert ok is True

    donation.status = "open"
    created = create_invitations(db_session, donation)
    db_session.commit()
    assert len(created) >= 1
    assert donation.status == "invited"


def test_compatible_category_only(db_session, seed_recipients):
    donation = _donation(category="vegan")
    db_session.add(donation)
    db_session.commit()
    created = create_invitations(db_session, donation)
    assert created == []


def test_tie_break_by_recipient_id(db_session):
    now = datetime.now(timezone.utc)
    donation = _donation()
    db_session.add(donation)
    r1 = Recipient(
        name="X",
        available_capacity=50,
        max_capacity=50,
        accepted_categories=["vegetarian"],
        preferred_categories=["vegetarian"],
        distance_km=5,
        earliest_pickup=now + timedelta(minutes=30),
        active=True,
    )
    r2 = Recipient(
        name="Y",
        available_capacity=50,
        max_capacity=50,
        accepted_categories=["vegetarian"],
        preferred_categories=["vegetarian"],
        distance_km=5,
        earliest_pickup=now + timedelta(minutes=30),
        active=True,
    )
    db_session.add_all([r1, r2])
    db_session.commit()
    ranked = rank_recipients(donation, [r1, r2], {})
    assert ranked[0]["score"] == ranked[1]["score"]
    assert ranked[0]["recipient"].id < ranked[1]["recipient"].id
