from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthUser, require_roles
from app.db.session import get_db
from app.services.demo import seed_demo

logger = logging.getLogger("foodbridge")
router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/seed")
def seed(
    force: bool = False,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    del user
    try:
        return seed_demo(db, force=force)
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Demo seed integrity error")
        raise HTTPException(
            status_code=409,
            detail="Demo seed conflict (duplicate rows). Try Reset & reseed again after redeploy.",
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Demo seed failed")
        raise HTTPException(
            status_code=500,
            detail=f"Demo seed failed: {exc}",
        ) from exc
