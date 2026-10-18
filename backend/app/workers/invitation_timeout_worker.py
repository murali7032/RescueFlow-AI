"""One-shot entry point for the scheduled Cloud Run timeout job."""

from __future__ import annotations

import logging

from app.db.session import SessionLocal
from app.services.timeouts import run_timeout_sweep

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        result = run_timeout_sweep(db)
        logger.info("Invitation timeout sweep complete: %s", result)
    except Exception:
        logger.exception("Invitation timeout sweep failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
