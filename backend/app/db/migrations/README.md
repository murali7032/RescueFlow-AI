# Migrations

Local/demo uses `AUTO_CREATE_TABLES=true` (`Base.metadata.create_all`).

For production PostgreSQL, prefer Alembic:

```bash
cd backend
pip install alembic
alembic init app/db/migrations
# configure sqlalchemy.url from DATABASE_URL
alembic revision --autogenerate -m "init"
alembic upgrade head
```

Keep `AUTO_CREATE_TABLES=false` in production once migrations own the schema.

### Invitation response expiry

Before deploying the timeout worker/API revision to an existing PostgreSQL
database, apply `20261018_invitation_expiry.sql` once using Cloud SQL Studio or
`psql`. It adds `invitations.expires_at`, backfills current rows using a
15-minute response window capped by the donation pickup deadline, and indexes
pending expirations. Local SQLite databases get forward-only expiry and donor
type upgrades at startup when `AUTO_CREATE_TABLES=true`; production PostgreSQL
databases need the SQL migration explicitly.

### Donor types and recipient reviews

Before deploying the donor type and review endpoints to PostgreSQL, apply
`20261018_donor_reviews.sql`. It adds the donor type field and review table.
Donor trust score is the average review rating scaled to 0–100 (50 before the
first review). After at least three reviews, a score at or below 40 pauses
submissions under that donor name pending support review.
