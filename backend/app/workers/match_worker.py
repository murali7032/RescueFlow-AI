"""Async matching worker interface.

Synchronous matching via create_invitations() is the default for the
demo. Call run_match_job when wiring Cloud Tasks / Pub/Sub later.
"""

from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.db.models import Donation
from app.services.matching import create_invitations

logger = logging.getLogger(__name__)


def run_match_job(donation_id: int) -> dict:
    db = SessionLocal()
    try:
        donation = db.get(Donation, donation_id)
        if donation is None:
            return {"ok": False, "error": "donation_not_found"}
        created = create_invitations(db, donation)
        db.commit()
        return {"ok": True, "created": len(created)}
    except Exception:
        db.rollback()
        logger.exception("match_worker failed for donation %s", donation_id)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("match_worker ready — invoke run_match_job(donation_id)")
