from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.agent import explain_match, explain_recovery
from app.auth import AuthUser, require_roles
from app.db.session import get_db
from app.schemas import ExplainMatchRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explain-match")
async def explain_match_endpoint(
    payload: ExplainMatchRequest,
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("donor", "admin")),
):
    result = await explain_match(db, payload.donation_id)
    if result.get("summary") == "Donation not found.":
        raise HTTPException(404, "Donation not found")
    if result.get("source") != "gemini":
        raise HTTPException(
            503,
            "Gemini could not produce a valid explanation after one retry. Please try again.",
        )
    return result


@router.get("/recovery-summary")
async def recovery_summary_endpoint(
    db: Session = Depends(get_db),
    user: AuthUser = Depends(require_roles("admin")),
):
    result = await explain_recovery(db)
    if result.get("source") != "gemini":
        raise HTTPException(
            503,
            "Gemini could not produce a valid recovery summary after one retry. Please try again.",
        )
    return result
