"""RescueFlow AI by FoodBridge — FastAPI entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    ai,
    allocations,
    demo,
    donations,
    donors,
    invitations,
    matches,
    recipients,
)
from app.config import get_settings
from app.db.session import Base, engine
from app.schemas import HealthOut

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("foodbridge")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-assisted surplus food recovery and allocation platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.auto_create_tables:
    # Local/dev convenience. Prefer Alembic migrations in production.
    Base.metadata.create_all(bind=engine)
    logger.info("Ensured database tables exist (AUTO_CREATE_TABLES=true)")

API_PREFIX = "/api/v1"
app.include_router(donations.router, prefix=API_PREFIX)
app.include_router(donors.router, prefix=API_PREFIX)
app.include_router(recipients.router, prefix=API_PREFIX)
app.include_router(invitations.router, prefix=API_PREFIX)
app.include_router(allocations.router, prefix=API_PREFIX)
app.include_router(matches.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(demo.router, prefix=API_PREFIX)


def _health() -> HealthOut:
    return HealthOut(
        status="ok",
        service="rescueflow-api",
        demo_mode=settings.demo_mode and not settings.is_production,
        database="sqlite" if settings.is_sqlite else "postgresql",
    )


@app.get("/health", response_model=HealthOut)
def health_root():
    return _health()


@app.get("/api/v1/health", response_model=HealthOut)
def health_v1():
    return _health()


@app.get("/")
def root():
    return {
        "product": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": API_PREFIX,
    }
