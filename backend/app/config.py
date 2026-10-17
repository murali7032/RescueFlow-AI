"""Environment settings for FoodBridge / RescueFlow AI.

Local defaults favour SQLite + demo auth + localhost CORS.
Production (ENVIRONMENT=production) requires Postgres, Firebase, and
explicit CORS_ORIGINS (Firebase Hosting / custom domains) — never "*".
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_CORS = (
    "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
    "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "RescueFlow AI by FoodBridge"
    environment: str = "development"
    database_url: str = "sqlite:///./foodbridge.db"
    auto_create_tables: bool = True
    demo_mode: bool = True
    log_level: str = "INFO"

    # Comma-separated browser origins. Required & non-wildcard in production.
    cors_origins: str = _LOCAL_CORS
    # Optional regex for extra origins (dev Cloud Shell only — ignored in prod).
    cors_origin_regex: str | None = None

    # Firebase Auth (required in production)
    firebase_project_id: str | None = None
    # Prefer ADC on Cloud Run. JSON only for local/CI if needed (Secret Manager).
    firebase_credentials_json: str | None = None

    # Vertex AI / Gemini
    google_cloud_project: str | None = None
    google_cloud_location: str = "asia-south1"
    google_genai_use_vertexai: bool = True
    gemini_model: str = "gemini-2.0-flash"
    ai_timeout_seconds: float = 12.0
    ai_enabled: bool = True

    # Matching weights
    weight_deadline: float = 0.35
    weight_capacity: float = 0.30
    weight_distance: float = 0.20
    weight_preference: float = 0.15

    # HTTP — OpenAPI docs disabled automatically in production
    docs_enabled: bool = True

    @field_validator(
        "demo_mode",
        "auto_create_tables",
        "ai_enabled",
        "google_genai_use_vertexai",
        "docs_enabled",
        mode="before",
    )
    @classmethod
    def _parse_bool(cls, value):  # noqa: ANN001
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def validate_for_runtime(self) -> list[str]:
        """Return human-readable errors. Empty list means OK to start."""
        errors: list[str] = []

        if not self.is_production:
            return errors

        if self.demo_mode:
            errors.append(
                "DEMO_MODE must be false when ENVIRONMENT=production "
                "(demo role headers are a security risk)."
            )

        if self.is_sqlite:
            errors.append(
                "DATABASE_URL must be PostgreSQL (Cloud SQL) in production, "
                "not SQLite."
            )

        if not self.cors_origin_list:
            errors.append(
                "CORS_ORIGINS is required in production. Set Firebase Hosting "
                "URLs, e.g. https://YOUR-donor.web.app,https://YOUR-recipient.web.app,"
                "https://YOUR-admin.web.app"
            )

# Allow wildcard '*' in CORS_ORIGINS (use with caution). Previously blocked in production.
# if any(o == "*" for o in self.cors_origin_list):
#     errors.append(
#         "CORS_ORIGINS must not contain '*', especially with credentials."
#     )

        for origin in self.cors_origin_list:
            if origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin:
                errors.append(
                    f"Insecure CORS origin in production (use https): {origin}"
                )

        if not self.firebase_project_id:
            errors.append(
                "FIREBASE_PROJECT_ID is required in production for token validation."
            )

        if not self.google_cloud_project:
            errors.append(
                "GOOGLE_CLOUD_PROJECT should be set on Cloud Run "
                "(needed for Vertex AI / ADC)."
            )

        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Backward-compatible module-level aliases used by session.py
_settings = get_settings()
DATABASE_URL = _settings.database_url
AUTO_CREATE_TABLES = _settings.auto_create_tables
