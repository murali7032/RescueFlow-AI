"""Safe synthetic demo seeding and reset."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    Allocation,
    AuditEvent,
    Donation,
    DonationReview,
    Invitation,
    Organization,
    Recipient,
    User,
)
from app.services.audit import record_event

_DEMO_FIREBASE_UIDS = ("demo-donor", "demo-recipient-a", "demo-admin")


def reset_demo_data(db: Session) -> None:
    """Remove demo-tagged rows and audit history tied to those rows."""
    demo_organization_ids = [
        r[0]
        for r in db.query(Organization.id)
        .filter(Organization.name.like("Demo %"))
        .all()
    ]
    demo_created_donation_ids = set()
    for (entity_id,) in (
        db.query(AuditEvent.entity_id)
        .filter(
            AuditEvent.entity_type == "donation",
            AuditEvent.actor_id.in_(_DEMO_FIREBASE_UIDS),
        )
        .all()
    ):
        try:
            demo_created_donation_ids.add(int(entity_id))
        except (TypeError, ValueError):
            continue

    donation_filters = [Donation.is_demo.is_(True)]
    if demo_organization_ids:
        donation_filters.append(
            Donation.organization_id.in_(demo_organization_ids)
        )
    if demo_created_donation_ids:
        donation_filters.append(
            Donation.id.in_(demo_created_donation_ids)
        )
    demo_donation_ids = [
        r[0]
        for r in db.query(Donation.id).filter(or_(*donation_filters)).all()
    ]
    demo_recipient_ids = [
        r[0]
        for r in db.query(Recipient.id).filter(Recipient.is_demo.is_(True)).all()
    ]
    demo_allocation_ids = [
        r[0]
        for r in db.query(Allocation.id)
        .filter(
            or_(
                Allocation.donation_id.in_(demo_donation_ids)
                if demo_donation_ids
                else False,
                Allocation.recipient_id.in_(demo_recipient_ids)
                if demo_recipient_ids
                else False,
            )
        )
        .all()
    ]
    demo_invitation_ids = [
        r[0]
        for r in db.query(Invitation.id)
        .filter(
            or_(
                Invitation.donation_id.in_(demo_donation_ids)
                if demo_donation_ids
                else False,
                Invitation.recipient_id.in_(demo_recipient_ids)
                if demo_recipient_ids
                else False,
            )
        )
        .all()
    ]

    # Audit events have polymorphic entity references rather than foreign keys.
    # Remove only events attached to demo donations, allocations, invitations,
    # plus the marker emitted when this synthetic dataset was seeded.
    audit_filters = [
        (AuditEvent.entity_type == "system")
        & (AuditEvent.entity_id == "demo")
        & (AuditEvent.action == "demo_seeded")
    ]
    if demo_donation_ids:
        audit_filters.append(
            (AuditEvent.entity_type == "donation")
            & AuditEvent.entity_id.in_([str(i) for i in demo_donation_ids])
        )
    if demo_allocation_ids:
        audit_filters.append(
            (AuditEvent.entity_type == "allocation")
            & AuditEvent.entity_id.in_([str(i) for i in demo_allocation_ids])
        )
    if demo_invitation_ids:
        audit_filters.append(
            (AuditEvent.entity_type == "invitation")
            & AuditEvent.entity_id.in_([str(i) for i in demo_invitation_ids])
        )
    db.query(AuditEvent).filter(or_(*audit_filters)).delete(
        synchronize_session=False
    )

    # Reviews reference allocations and donations. Remove reviews first, even
    # when only the recipient side of a demo allocation is being reset.
    review_filters = []
    if demo_donation_ids:
        review_filters.append(DonationReview.donation_id.in_(demo_donation_ids))
    if demo_allocation_ids:
        review_filters.append(DonationReview.allocation_id.in_(demo_allocation_ids))
    if review_filters:
        db.query(DonationReview).filter(or_(*review_filters)).delete(
            synchronize_session=False
        )

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

    # Delete ALL demo users (donor/admin are not linked via recipient_id).
    # Leaving them causes UniqueViolation on firebase_uid when re-seeding.
    db.query(User).filter(
        (User.firebase_uid.in_(_DEMO_FIREBASE_UIDS))
        | (User.email.like("%@demo.foodbridge.local"))
    ).delete(synchronize_session=False)

    if demo_recipient_ids:
        db.query(Recipient).filter(Recipient.id.in_(demo_recipient_ids)).delete(
            synchronize_session=False
        )

    if demo_organization_ids:
        db.query(Organization).filter(
            Organization.id.in_(demo_organization_ids)
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
            "label": "SYNTHETIC DEMO DATA",
        }

    now = datetime.now(timezone.utc)
    orgs = [
        Organization(name="Demo Harbor Bistro", org_type="donor", active=True),
        Organization(name="Demo Community Kitchen A", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen B", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen C", org_type="recipient", active=True),
        Organization(name="Demo Community Kitchen D", org_type="recipient", active=True),
        Organization(name="Demo Neighborhood Pantry E", org_type="recipient", active=True),
        Organization(name="Demo Family Meal Center F", org_type="recipient", active=True),
        Organization(name="Demo Senior Support Kitchen G", org_type="recipient", active=True),
        Organization(name="Demo Campus Food Hub H", org_type="recipient", active=True),
        Organization(name="Demo Zero-Capacity Kitchen I", org_type="recipient", active=True),
        Organization(name="Demo Inactive Kitchen J", org_type="recipient", active=False),
        Organization(name="Demo Meat-Only Pantry K", org_type="recipient", active=True),
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
        Recipient(
            name="Neighborhood Pantry E",
            organization_id=orgs[5].id,
            available_capacity=45,
            max_capacity=60,
            accepted_categories=["vegetarian", "vegan", "bakery"],
            preferred_categories=["vegetarian", "vegan"],
            distance_km=4.5,
            earliest_pickup=now + timedelta(minutes=25),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Family Meal Center F",
            organization_id=orgs[6].id,
            available_capacity=120,
            max_capacity=140,
            accepted_categories=["vegetarian", "vegan", "prepared_meals"],
            preferred_categories=["prepared_meals"],
            distance_km=11,
            earliest_pickup=now + timedelta(minutes=50),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Senior Support Kitchen G",
            organization_id=orgs[7].id,
            available_capacity=35,
            max_capacity=45,
            accepted_categories=["vegetarian", "vegan", "bakery"],
            preferred_categories=["vegetarian"],
            distance_km=5.5,
            earliest_pickup=now + timedelta(minutes=35),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Campus Food Hub H",
            organization_id=orgs[8].id,
            available_capacity=90,
            max_capacity=100,
            accepted_categories=["vegetarian", "vegan", "produce"],
            preferred_categories=["produce", "vegetarian"],
            distance_km=9,
            earliest_pickup=now + timedelta(minutes=45),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Zero-Capacity Kitchen I",
            organization_id=orgs[9].id,
            available_capacity=0,
            max_capacity=80,
            accepted_categories=["vegetarian", "vegan"],
            preferred_categories=["vegetarian"],
            distance_km=2.5,
            earliest_pickup=now + timedelta(minutes=15),
            active=True,
            is_demo=True,
        ),
        Recipient(
            name="Inactive Kitchen J",
            organization_id=orgs[10].id,
            available_capacity=90,
            max_capacity=90,
            accepted_categories=["vegetarian", "vegan"],
            preferred_categories=["vegetarian"],
            distance_km=1.5,
            earliest_pickup=now + timedelta(minutes=15),
            active=False,
            is_demo=True,
        ),
        Recipient(
            name="Meat-Only Pantry K",
            organization_id=orgs[11].id,
            available_capacity=60,
            max_capacity=60,
            accepted_categories=["meat"],
            preferred_categories=["meat"],
            distance_km=7,
            earliest_pickup=now + timedelta(minutes=30),
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
            organization_id=orgs[-1].id,
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
