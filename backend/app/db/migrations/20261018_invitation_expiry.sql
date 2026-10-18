-- Apply once to the production PostgreSQL database before deploying the API
-- revision that writes or reads invitations.expires_at.
BEGIN;

ALTER TABLE invitations
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

UPDATE invitations AS i
SET expires_at = LEAST(
    i.created_at + INTERVAL '15 minutes',
    d.pickup_deadline
)
FROM donations AS d
WHERE d.id = i.donation_id
  AND i.expires_at IS NULL;

ALTER TABLE invitations
    ALTER COLUMN expires_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_invitations_pending_expires_at
    ON invitations (expires_at)
    WHERE status = 'pending';

COMMIT;
