from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import AuthUser, require_roles
from app.config import get_settings
from app.db.session import get_db
from app.services.demo import seed_demo

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
def seed(
    force: bool = False,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    settings = get_settings()
    if not settings.demo_mode:
        raise HTTPException(403, "DEMO_MODE is disabled")
    return seed_demo(db, force=force)
