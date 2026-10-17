"""Authentication and role-based authorization.

Production: Firebase ID token validation when FIREBASE_PROJECT_ID is set.
Development/demo: X-Demo-Role / X-Demo-User-Id headers when DEMO_MODE=true.
Demo headers are rejected when environment=production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db


@dataclass
class AuthUser:
    uid: str
    email: str
    role: str  # donor | recipient | admin
    display_name: str
    recipient_id: int | None = None
    organization_id: int | None = None
    auth_method: str = "demo"


def _verify_firebase_token(token: str) -> dict:
    """Validate Firebase ID token. Raises on failure."""
    settings = get_settings()
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth, credentials
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="firebase-admin is not installed; cannot validate tokens",
        ) from exc

    if not firebase_admin._apps:
        if settings.firebase_credentials_json:
            import json

            cred = credentials.Certificate(
                json.loads(settings.firebase_credentials_json)
            )
            firebase_admin.initialize_app(cred)
        else:
            # Application Default Credentials (Cloud Run / gcloud)
            firebase_admin.initialize_app()

    try:
        return fb_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {exc}",
        ) from exc


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    x_demo_role: Annotated[str | None, Header()] = None,
    x_demo_user_id: Annotated[str | None, Header()] = None,
    x_demo_recipient_id: Annotated[int | None, Header()] = None,
    db: Session = Depends(get_db),
) -> AuthUser:
    settings = get_settings()

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if settings.firebase_project_id:
            claims = _verify_firebase_token(token)
            role = claims.get("role") or claims.get("foodbridge_role") or "donor"
            return AuthUser(
                uid=claims.get("uid") or claims.get("sub") or "unknown",
                email=claims.get("email") or "",
                role=role,
                display_name=claims.get("name") or claims.get("email") or "User",
                recipient_id=claims.get("recipient_id"),
                organization_id=claims.get("organization_id"),
                auth_method="firebase",
            )
        # Token present but Firebase not configured
        raise HTTPException(
            401,
            "Bearer tokens require FIREBASE_PROJECT_ID to be configured",
        )

    # Demo auth — never available in production
    if settings.demo_mode and not settings.is_production:
        role = (x_demo_role or "admin").lower()
        if role not in {"donor", "recipient", "admin"}:
            raise HTTPException(400, "X-Demo-Role must be donor|recipient|admin")
        return AuthUser(
            uid=x_demo_user_id or f"demo-{role}",
            email=f"{role}@demo.foodbridge.local",
            role=role,
            display_name=f"Demo {role.title()}",
            recipient_id=x_demo_recipient_id,
            auth_method="demo",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def require_roles(*roles: str):
    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted. Required: {roles}",
            )
        return user

    return _dep
