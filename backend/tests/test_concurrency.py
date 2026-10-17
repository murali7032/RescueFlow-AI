"""Concurrent acceptance tests — require PostgreSQL.

Set CONCURRENCY_DATABASE_URL to a disposable Postgres database, e.g.:
  postgresql+psycopg2://postgres:postgres@localhost:5432/foodbridge_test
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import pytest

PG_URL = os.getenv("CONCURRENCY_DATABASE_URL") or os.getenv("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="PostgreSQL required for concurrency locking tests",
)


@pytest.fixture()
def pg_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", PG_URL)
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    # Re-import engine pieces is hard; use local engine instead
    yield PG_URL


def test_concurrent_accept_does_not_over_allocate(pg_env):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.models import Allocation, Donation, Invitation, Recipient
    from app.db.session import Base
    from app.services.allocations import accept_invitation
    from app.services.matching import create_invitations

    engine = create_engine(pg_env, pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as db:
        now = datetime.now(timezone.utc)
        # Two recipients each offered overlapping stock
        r1 = Recipient(
            name="R1",
            available_capacity=100,
            max_capacity=100,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=1,
            earliest_pickup=now + timedelta(minutes=10),
            active=True,
        )
        r2 = Recipient(
            name="R2",
            available_capacity=100,
            max_capacity=100,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=2,
            earliest_pickup=now + timedelta(minutes=10),
            active=True,
        )
        db.add_all([r1, r2])
        donation = Donation(
            donor_name="Concurrent Cafe",
            category="vegetarian",
            total_portions=100,
            remaining_portions=100,
            pickup_deadline=now + timedelta(hours=2),
            status="open",
        )
        db.add(donation)
        db.commit()
        create_invitations(db, donation)
        db.commit()
        invites = (
            db.query(Invitation)
            .filter(Invitation.donation_id == donation.id, Invitation.status == "pending")
            .all()
        )
        assert len(invites) >= 1
        # Force both invitations to suggest 100 to create a conflict window
        for inv in invites:
            inv.suggested_portions = 100
        db.commit()
        invite_ids = [i.id for i in invites]
        donation_id = donation.id

    def _accept(iid: int):
        with Session() as db:
            try:
                alloc = accept_invitation(db, iid)
                return ("ok", alloc.portions)
            except Exception as exc:
                return ("err", str(exc))

    results = []
    with ThreadPoolExecutor(max_workers=len(invite_ids)) as pool:
        futures = [pool.submit(_accept, iid) for iid in invite_ids]
        for f in as_completed(futures):
            results.append(f.result())

    with Session() as db:
        donation = db.get(Donation, donation_id)
        total = (
            db.query(Allocation)
            .filter(Allocation.donation_id == donation_id)
            .all()
        )
        allocated = sum(a.portions for a in total)
        assert allocated <= 100
        assert donation.remaining_portions >= 0
        assert allocated + donation.remaining_portions == 100

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
