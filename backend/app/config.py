"""Environment settings for FoodBridge / RescueFlow AI."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RescueFlow AI by FoodBridge"
    environment: str = "development"
    database_url: str = "sqlite:///./foodbridge.db"
    auto_create_tables: bool = True
    demo_mode: bool = True
    log_level: str = "INFO"

    # CORS — comma-separated origins. Never use * with credentials in production.
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"

    # Firebase (optional). When unset, demo auth may be used if demo_mode=True.
    firebase_project_id: str | None = None
    firebase_credentials_json: str | None = None

    # Vertex AI / Gemini
    google_cloud_project: str | None = None
    google_cloud_location: str = "asia-south1"
    google_genai_use_vertexai: bool = True
    gemini_model: str = "gemini-2.0-flash"
    ai_timeout_seconds: float = 12.0
    ai_enabled: bool = True

    # Matching weights (must sum to 1.0)
    weight_deadline: float = 0.35
    weight_capacity: float = 0.30
    weight_distance: float = 0.20
    weight_preference: float = 0.15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./foodbridge.db"),
        auto_create_tables=os.getenv("AUTO_CREATE_TABLES", "true").lower() == "true",
        demo_mode=os.getenv("DEMO_MODE", "true").lower() == "true",
        environment=os.getenv("ENVIRONMENT", "development"),
        cors_origins=os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175",
        ),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID"),
        google_cloud_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        google_cloud_location=os.getenv("GOOGLE_CLOUD_LOCATION", "asia-south1"),
        google_genai_use_vertexai=os.getenv(
            "GOOGLE_GENAI_USE_VERTEXAI", "true"
        ).lower()
        == "true",
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        ai_enabled=os.getenv("AI_ENABLED", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


# Backward-compatible module-level aliases used by session.py
_settings = get_settings()
DATABASE_URL = _settings.database_url
AUTO_CREATE_TABLES = _settings.auto_create_tables
