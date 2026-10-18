"""Small forward-only schema upgrades for persistent local SQLite databases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade_sqlite_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        donation_columns = {column["name"] for column in inspector.get_columns("donations")}
        if "donor_type" not in donation_columns:
            connection.execute(
                text(
                    "ALTER TABLE donations ADD COLUMN donor_type "
                    "VARCHAR(30) NOT NULL DEFAULT 'restaurant'"
                )
            )

        invitation_columns = {
            column["name"] for column in inspector.get_columns("invitations")
        }
        if "expires_at" not in invitation_columns:
            connection.execute(
                text("ALTER TABLE invitations ADD COLUMN expires_at DATETIME")
            )
        connection.execute(
            text(
                """UPDATE invitations
                SET expires_at = (
                    SELECT MIN(datetime(invitations.created_at, '+15 minutes'),
                               datetime(donations.pickup_deadline))
                    FROM donations
                    WHERE donations.id = invitations.donation_id
                )
                WHERE expires_at IS NULL"""
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_invitations_pending_expires_at "
                "ON invitations (expires_at) WHERE status = 'pending'"
            )
        )
