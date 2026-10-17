CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (
        type IN ('donor', 'recipient', 'admin')
    ),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE donation_listings (
    id UUID PRIMARY KEY,
    donor_id UUID NOT NULL REFERENCES organizations(id),
    food_name TEXT NOT NULL,
    food_type TEXT NOT NULL CHECK (
        food_type IN ('vegetarian', 'vegan', 'mixed')
    ),
    total_portions INTEGER NOT NULL CHECK (total_portions > 0),
    available_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (
        status IN (
            'open', 'matching', 'partially_allocated',
            'allocated', 'cancelled', 'expired', 'completed'
        )
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (expires_at > available_at)
);

CREATE TABLE recipient_requirements (
    id UUID PRIMARY KEY,
    recipient_id UUID NOT NULL REFERENCES organizations(id),
    food_types TEXT[] NOT NULL,
    required_portions INTEGER NOT NULL DEFAULT 0
        CHECK (required_portions >= 0),
    max_capacity INTEGER NOT NULL CHECK (max_capacity >= 0),
    available_from TIMESTAMPTZ NOT NULL,
    available_until TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (available_until > available_from)
);

CREATE TABLE match_invitations (
    id UUID PRIMARY KEY,
    donation_id UUID NOT NULL REFERENCES donation_listings(id),
    recipient_id UUID NOT NULL REFERENCES organizations(id),
    offered_portions INTEGER NOT NULL CHECK (offered_portions > 0),
    score NUMERIC(5,2),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN (
            'pending', 'accepted', 'declined',
            'expired', 'withdrawn'
        )
    ),
    expires_at TIMESTAMPTZ NOT NULL,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invitations_recipient_status
    ON match_invitations(recipient_id, status);

CREATE INDEX idx_invitations_donation_status
    ON match_invitations(donation_id, status);

CREATE TABLE allocations (
    id UUID PRIMARY KEY,
    donation_id UUID NOT NULL REFERENCES donation_listings(id),
    recipient_id UUID NOT NULL REFERENCES organizations(id),
    invitation_id UUID REFERENCES match_invitations(id),
    portions INTEGER NOT NULL CHECK (portions > 0),
    status TEXT NOT NULL DEFAULT 'reserved' CHECK (
        status IN ('reserved', 'confirmed', 'picked_up', 'cancelled')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_allocations_donation_status
    ON allocations(donation_id, status);

CREATE TABLE audit_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id UUID REFERENCES organizations(id),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);