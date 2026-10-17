"""SQLAlchemy models for RescueFlow AI."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    org_type: Mapped[str] = mapped_column(String(30))  # donor | recipient | admin
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(30))  # donor | recipient | admin
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    recipient_id: Mapped[int | None] = mapped_column(
        ForeignKey("recipients.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Donation(Base):
    __tablename__ = "donations"

    id: Mapped[int] = mapped_column(primary_key=True)
    donor_name: Mapped[str] = mapped_column(String(120))
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(60))
    food_name: Mapped[str] = mapped_column(String(160), default="Surplus meal")
    total_portions: Mapped[int] = mapped_column(Integer)
    remaining_portions: Mapped[int] = mapped_column(Integer)
    pickup_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_address: Mapped[str] = mapped_column(String(255), default="Demo kitchen")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # open | partially_allocated | allocated | expired | cancelled
    status: Mapped[str] = mapped_column(String(30), default="open")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    invitations = relationship("Invitation", back_populates="donation")
    allocations = relationship("Allocation", back_populates="donation")


class Recipient(Base):
    __tablename__ = "recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    available_capacity: Mapped[int] = mapped_column(Integer)
    max_capacity: Mapped[int] = mapped_column(Integer, default=0)
    accepted_categories: Mapped[list] = mapped_column(JSON)
    preferred_categories: Mapped[list] = mapped_column(JSON, default=list)
    # Synthetic demo distance — not live traffic/routing.
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    earliest_pickup: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    invitations = relationship("Invitation", back_populates="recipient")
    allocations = relationship("Allocation", back_populates="recipient")


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("recipients.id"))
    suggested_portions: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # pending | accepted | declined | cancelled | expired
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    donation = relationship("Donation", back_populates="invitations")
    recipient = relationship("Recipient", back_populates="invitations")


class Allocation(Base):
    __tablename__ = "allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id"))
    recipient_id: Mapped[int] = mapped_column(ForeignKey("recipients.id"))
    invitation_id: Mapped[int] = mapped_column(ForeignKey("invitations.id"))
    portions: Mapped[int] = mapped_column(Integer)
    # pending | confirmed | completed | failed
    pickup_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    pickup_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    pickup_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    donation = relationship("Donation", back_populates="allocations")
    recipient = relationship("Recipient", back_populates="allocations")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_role: Mapped[str | None] = mapped_column(String(30), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
