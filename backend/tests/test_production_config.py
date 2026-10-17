from __future__ import annotations

import os

import pytest

from app.config import Settings


def test_production_rejects_localhost_only_defaults():
    settings = Settings(
        environment="production",
        demo_mode=False,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="",
        firebase_project_id="proj",
        google_cloud_project="proj",
    )
    errors = settings.validate_for_runtime()
    assert any("CORS_ORIGINS" in e for e in errors)


def test_production_rejects_wildcard_cors():
    settings = Settings(
        environment="production",
        demo_mode=False,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="*",
        firebase_project_id="proj",
        google_cloud_project="proj",
    )
    errors = settings.validate_for_runtime()
    assert any("*" in e or "wildcard" in e.lower() or "must not contain" in e for e in errors)


def test_production_ok_with_firebase_hosting_origins():
    settings = Settings(
        environment="production",
        demo_mode=False,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="https://foodbridge-donor.web.app,https://foodbridge-admin.web.app",
        firebase_project_id="proj",
        google_cloud_project="proj",
    )
    assert settings.validate_for_runtime() == []


def test_development_allows_sqlite_demo():
    settings = Settings(
        environment="development",
        demo_mode=True,
        database_url="sqlite:///./foodbridge.db",
        cors_origins="http://localhost:5173",
    )
    assert settings.validate_for_runtime() == []
