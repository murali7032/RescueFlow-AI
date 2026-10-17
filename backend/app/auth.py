"""Authentication and role-based authorization.

Cloud Run / cup demo: X-Demo-* headers when DEMO_MODE=true.
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


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    x_demo_role: Annotated[str | None, Header()] = None,
    x_demo_user_id: Annotated[str | None, Header()] = None,
    x_demo_recipient_id: Annotated[int | None, Header()] = None,
    db: Session = Depends(get_db),
) -> AuthUser:
    del db  # reserved for user lookup enrichment
    del authorization  # reserved if a future token auth is added
    settings = get_settings()

    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (DEMO_MODE must be enabled)",
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


def require_roles(*roles: str):
    def _dep(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted. Required: {roles}",
            )
        return user

    return _dep
