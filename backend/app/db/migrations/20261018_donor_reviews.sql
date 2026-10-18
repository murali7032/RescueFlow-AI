-- Apply before deploying backend code that stores donor types and reviews.
BEGIN;

ALTER TABLE donations
    ADD COLUMN IF NOT EXISTS donor_type VARCHAR(30) NOT NULL DEFAULT 'restaurant';

CREATE TABLE IF NOT EXISTS donation_reviews (
    id SERIAL PRIMARY KEY,
    donation_id INTEGER NOT NULL REFERENCES donations(id),
    allocation_id INTEGER NOT NULL UNIQUE REFERENCES allocations(id),
    recipient_id INTEGER NOT NULL REFERENCES recipients(id),
    donor_organization_id INTEGER REFERENCES organizations(id),
    donor_name VARCHAR(120) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donation_reviews_donor_name
    ON donation_reviews (LOWER(donor_name));

CREATE INDEX IF NOT EXISTS idx_donation_reviews_donor_organization
    ON donation_reviews (donor_organization_id);

COMMIT;
