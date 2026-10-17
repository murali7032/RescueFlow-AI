from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Configure test env before importing the app
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["DEMO_MODE"] = "true"
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["AI_ENABLED"] = "false"

from app.config import get_settings

get_settings.cache_clear()

from app.db.session import Base, get_db
from app.main import app
from app.db.models import Recipient


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine):
    TestingSession = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)

    def _override():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    def _headers(role: str = "admin", recipient_id: int | None = None):
        h = {"X-Demo-Role": role, "X-Demo-User-Id": f"test-{role}"}
        if recipient_id is not None:
            h["X-Demo-Recipient-Id"] = str(recipient_id)
        return h

    return _headers


@pytest.fixture()
def seed_recipients(db_session):
    now = datetime.now(timezone.utc)
    recipients = [
        Recipient(
            name="Community Kitchen A",
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
            name="Community Kitchen D",
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
            name="Inactive Kitchen",
            available_capacity=90,
            max_capacity=90,
            accepted_categories=["vegetarian"],
            preferred_categories=["vegetarian"],
            distance_km=1,
            earliest_pickup=now + timedelta(minutes=15),
            active=False,
            is_demo=True,
        ),
    ]
    db_session.add_all(recipients)
    db_session.commit()
    for r in recipients:
        db_session.refresh(r)
    return recipients


@pytest.fixture()
def future_deadline():
    return (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat().replace(
        "+00:00", "Z"
    )
