"""RescueFlow AI by FoodBridge — FastAPI entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

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
from app.db.migrations.sqlite import upgrade_sqlite_schema
from app.schemas import HealthOut

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger("foodbridge")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    errors = settings.validate_for_runtime()
    if errors:
        for err in errors:
            logger.error("Startup configuration error: %s", err)
        raise RuntimeError(
            "Invalid production configuration:\n- " + "\n- ".join(errors)
        )

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        upgrade_sqlite_schema(engine)
        logger.info("Ensured database tables exist (AUTO_CREATE_TABLES=true)")
    else:
        logger.info("AUTO_CREATE_TABLES=false — expecting migrations already applied")

    logger.info(
        "Started env=%s demo_mode=%s db=%s cors_origins=%s",
        settings.environment,
        settings.demo_mode,
        "sqlite" if settings.is_sqlite else "postgresql",
        settings.cors_origin_list,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="AI-assisted surplus food recovery and allocation platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled and not settings.is_production else None,
    redoc_url="/redoc" if settings.docs_enabled and not settings.is_production else None,
)

_allow_all = "*" in settings.cors_origin_list
_cors_kw: dict = {
    "allow_origins": ["*"] if _allow_all else settings.cors_origin_list,
    "allow_credentials": not _allow_all,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": [
        "Authorization",
        "Content-Type",
        "X-Demo-Role",
        "X-Demo-User-Id",
        "X-Demo-Recipient-Id",
        "X-Request-Id",
    ],
}

# Dev-only helpers: Cloud Shell preview + optional custom regex.
# Never enable open regexes in production.
if not settings.is_production:
    _cors_kw["allow_origin_regex"] = (
        settings.cors_origin_regex or r"https://.*\.cloudshell\.dev$"
    )
elif settings.cors_origin_regex:
    logger.warning(
        "CORS_ORIGIN_REGEX is set but ignored when ENVIRONMENT=production; "
        "list exact origins in CORS_ORIGINS instead."
    )

app.add_middleware(CORSMiddleware, **_cors_kw)

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
        demo_mode=settings.demo_mode,
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
        "health": "/health",
        "api": API_PREFIX,
        "environment": settings.environment,
        "docs": "/docs" if settings.docs_enabled and not settings.is_production else None,
    }
