"""Safe synthetic demo seeding and reset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models import (
    Allocation,
    AuditEvent,
    Donation,
    Invitation,
    Organization,
    Recipient,
    User,
)
from app.services.audit import record_event


def reset_demo_data(db: Session) -> None:
    """Remove demo-tagged rows and related invitations/allocations."""
    demo_donation_ids = [
        r[0]
        for r in db.query(Donation.id).filter(Donation.is_demo.is_(True)).all()
    ]
    demo_recipient_ids = [
        r[0]
        for r in db.query(Recipient.id).filter(Recipient.is_demo.is_(True)).all()
    ]

    if demo_donation_ids:
        db.query(Allocation).filter(
            Allocation.donation_id.in_(demo_donation_ids)
        ).delete(synchronize_session=False)
        db.query(Invitation).filter(
            Invitation.donation_id.in_(demo_donation_ids)
        ).delete(synchronize_session=False)
        db.query(Donation).filter(Donation.id.in_(demo_donation_ids)).delete(
            synchronize_session=False
        )

    if demo_recipient_ids:
        db.query(Invitation).filter(
            Invitation.recipient_id.in_(demo_recipient_ids)
        ).delete(synchronize_session=False)
        db.query(Allocation).filter(
            Allocation.recipient_id.in_(demo_recipient_ids)
        ).delete(synchronize_session=False)
        db.query(User).filter(User.recipient_id.in_(demo_recipient_ids)).delete(
            synchronize_session=False
        )
        db.query(Recipient).filter(Recipient.id.in_(demo_recipient_ids)).delete(
            synchronize_session=False
        )

    db.query(Organization).filter(
        Organization.name.like("Demo %")
    ).delete(synchronize_session=False)
    db.commit()


def seed_demo(db: Session, *, force: bool = False) -> dict:
    if force:
        reset_demo_data(db)

    existing = (
        db.query(Recipient).filter(Recipient.is_demo.is_(True)).count()
    )
    if existing > 0 and not force:
        return {
            "message": "Demo recipients already seeded",
            "count": existing,
            "reset": False,
        }

    now = datetime.now(timezone.utc)
    orgs = [
        Organization(name="Demo Harbor Bistro", org_type="donor", active=True),
        Organization(name="Demo Community Kitchen A", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen B", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen C", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen D", org_type="recipient", active=True),
        Organization(name="Demo FoodBridge Admin", org_type="admin", active=True),
    ]
    db.add_all(orgs)
    db.flush()

    recipients = [
        Recipient(
            name="Community Kitchen A",
            organization_id=orgs[1].id,
            available_capacity=80,
            max_capacity=80,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=3,
            earliest_pickup=now + timedelta(minutes=20),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Community Kitchen B",
            organization_id=orgs[2].id,
            available_capacity=70,
            max_capacity=70,
            accepted_categories=["vegetarian"],
            preferred_categories=[],
            distance_km=6,
            earliest_pickup=now + timedelta(minutes=30),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Community Kitchen C",
            organization_id=orgs[3].id,
            available_capacity=50,
            max_capacity=50,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=8,
            earliest_pickup=now + timedelta(minutes=40),
            active=True,
            is_demo=True,
        ),
        Recipient(
            # Cannot collect before a typical 2h demo deadline when donation
            # is created shortly after seed — earliest_pickup is +3h.
            name="Community Kitchen D",
            organization_id=orgs[4].id,
            available_capacity=100,
            max_capacity=100,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=2,
            earliest_pickup=now + timedelta(hours=3),
            active=True,
            is_demo=True,
        ),
    ]
    db.add_all(recipients)
    db.flush()

    users = [
        User(
            email="donor@demo.foodbridge.local",
            display_name="Demo Donor",
            role="donor",
            organization_id=orgs[0].id,
            firebase_uid="demo-donor",
        ),
        User(
            email="recipient-a@demo.foodbridge.local",
            display_name="Demo Recipient A",
            role="recipient",
            organization_id=orgs[1].id,
            recipient_id=recipients[0].id,
            firebase_uid="demo-recipient-a",
        ),
        User(
            email="admin@demo.foodbridge.local",
            display_name="Demo Admin",
            role="admin",
            organization_id=orgs[5].id,
            firebase_uid="demo-admin",
        ),
    ]
    db.add_all(users)

    record_event(
        db,
        entity_type="system",
        entity_id="demo",
        action="demo_seeded",
        details={"recipients": len(recipients), "note": "Synthetic demo data"},
    )
    db.commit()

    return {
        "message": "Synthetic demo recipients created",
        "count": len(recipients),
        "recipients": [
            {
                "id": r.id,
                "name": r.name,
                "available_capacity": r.available_capacity,
                "distance_km": r.distance_km,
                "earliest_pickup": r.earliest_pickup.isoformat(),
            }
            for r in recipients
        ],
        "reset": force,
        "label": "SYNTHETIC DEMO DATA",
    }
