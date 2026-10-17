"""Authentication and role-based authorization.

Production: Firebase ID token validation (FIREBASE_PROJECT_ID required).
Development: optional X-Demo-* headers when DEMO_MODE=true and not production.
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
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        if settings.firebase_credentials_json:
            import json

            cred = credentials.Certificate(
                json.loads(settings.firebase_credentials_json)
            )
            firebase_admin.initialize_app(cred, options)
        else:
            # Cloud Run: Application Default Credentials
            firebase_admin.initialize_app(options=options)

    try:
        decoded = fb_auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        ) from exc

    if (
        settings.firebase_project_id
        and decoded.get("aud")
        and decoded.get("aud") != settings.firebase_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience does not match FIREBASE_PROJECT_ID",
        )
    return decoded


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    x_demo_role: Annotated[str | None, Header()] = None,
    x_demo_user_id: Annotated[str | None, Header()] = None,
    x_demo_recipient_id: Annotated[int | None, Header()] = None,
    db: Session = Depends(get_db),
) -> AuthUser:
    del db  # reserved for user lookup enrichment
    settings = get_settings()

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        if not settings.firebase_project_id:
            raise HTTPException(
                401,
                "Bearer tokens require FIREBASE_PROJECT_ID to be configured",
            )
        claims = _verify_firebase_token(token)
        role = (
            claims.get("role")
            or claims.get("foodbridge_role")
            or (claims.get("claims") or {}).get("role")
            or "donor"
        )
        if role not in {"donor", "recipient", "admin"}:
            raise HTTPException(403, f"Unsupported role claim: {role}")
        return AuthUser(
            uid=str(claims.get("uid") or claims.get("sub") or "unknown"),
            email=str(claims.get("email") or ""),
            role=str(role),
            display_name=str(
                claims.get("name") or claims.get("email") or "User"
            ),
            recipient_id=_as_optional_int(
                claims.get("recipient_id")
                or (claims.get("claims") or {}).get("recipient_id")
            ),
            organization_id=_as_optional_int(
                claims.get("organization_id")
                or (claims.get("claims") or {}).get("organization_id")
            ),
            auth_method="firebase",
        )

    # Demo auth — never available in production
    if settings.is_production or not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (Bearer Firebase ID token)",
        )

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


def _as_optional_int(value) -> int | None:  # noqa: ANN001
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def require_roles(*roles: str):
    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted. Required: {roles}",
            )
        return user

    return _dep
