from __future__ import annotations

from app.config import Settings


def test_production_rejects_empty_cors():
    settings = Settings(
        environment="production",
        demo_mode=True,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="",
        google_cloud_project="proj",
    )
    errors = settings.validate_for_runtime()
    assert any("CORS_ORIGINS" in e for e in errors)


def test_production_rejects_demo_mode_false():
    settings = Settings(
        environment="production",
        demo_mode=False,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="https://foodbridge-donor-ui-xxxx.a.run.app",
        google_cloud_project="proj",
    )
    errors = settings.validate_for_runtime()
    assert any("DEMO_MODE" in e for e in errors)


def test_production_ok_with_cloud_run_ui_origins():
    settings = Settings(
        environment="production",
        demo_mode=True,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins=(
            "https://foodbridge-donor-ui-xxxx.a.run.app,"
            "https://foodbridge-admin-ui-xxxx.a.run.app"
        ),
        google_cloud_project="proj",
    )
    assert settings.validate_for_runtime() == []


def test_production_allows_wildcard_cors_first_boot():
    settings = Settings(
        environment="production",
        demo_mode=True,
        database_url="postgresql+psycopg2://u:p@/db?host=/cloudsql/x",
        cors_origins="*",
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
