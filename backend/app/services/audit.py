"""Audit event helpers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record_event(
    db: Session,
    *,
    entity_type: str,
    entity_id: str | int,
    action: str,
    details: dict | None = None,
    actor_role: str | None = None,
    actor_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_role=actor_role,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        details=details or {},
    )
    db.add(event)
    return event
