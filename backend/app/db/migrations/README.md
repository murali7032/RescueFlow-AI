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
