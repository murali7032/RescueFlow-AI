# Troubleshooting

## Python / pip

- **Locked `uvicorn.exe` on Windows:** stop the running API process, or use a fresh venv (`.venv_ci`).
- **Import `app` fails:** set `PYTHONPATH` to the `backend` directory.
- **Schema mismatch after model changes:** delete local `foodbridge.db` or set a new `DATABASE_URL`; with `AUTO_CREATE_TABLES=true` tables are created but not migrated.

## Node / Vite

- **Alias `@foodbridge/shared` not found:** ensure `vite.config.ts` points to `../shared`.
- **Build fails on TS:** run `npx tsc --noEmit` in the app folder for details.
- **Blank API calls:** set `VITE_API_URL` to the backend origin (no trailing slash).

## Database

- **SQLite `database is locked`:** close other uvicorn processes; avoid concurrency tests on SQLite.
- **Postgres connection refused:** verify Cloud SQL Auth Proxy / `--add-cloudsql-instances` and secret `DATABASE_URL`.
- **FOR UPDATE no-op on SQLite:** expected; use Postgres for concurrency proof.

## CORS

- Browser blocked: add the **exact** frontend origin to `CORS_ORIGINS` (comma-separated HTTPS Cloud Run UI URLs).
- Prefer exact UI origins over `*` after first boot. Localhost defaults are for development only.
- After deploying UIs, update the API:  
  `gcloud run services update foodbridge-rescueflow --update-env-vars=CORS_ORIGINS=https://...`
- Cloud Run `--set-env-vars` treats commas as separators — `deploy/deploy.sh` uses the `^@^` delimiter so `CORS_ORIGINS` can include multiple sites.

### Cloud Shell Web Preview (`forwardAuthCookie` / preflight redirect)

Calling `https://8000-….cloudshell.dev` from `https://5173-….cloudshell.dev` fails: Cloud Shell redirects the OPTIONS preflight for auth cookies, and browsers forbid redirects on preflight.

**Fix:** do **not** set `VITE_API_URL` to the port-8000 preview URL. Leave it unset/empty so the UI calls same-origin `/api/...`. Vite proxies to `http://127.0.0.1:8000`.

```bash
# Terminal 1 — API on 8000 (keep Web Preview on the frontend port only)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — open Web Preview on 5173
cd frontend && npm run dev -- --host 0.0.0.0 --port 5173
```

Restart Vite after pulling this change so the proxy loads.

## Auth

- **401:** ensure `DEMO_MODE=true` and send `X-Demo-Role: admin|donor|recipient`.
- **403 role:** check `X-Demo-Role` matches the endpoint’s required role.
- **Recipient 400:** set `X-Demo-Recipient-Id` or `?recipient_id=`.

## Cloud Run

- Container must listen on `0.0.0.0:$PORT` (Dockerfile uses uvicorn `--port ${PORT}`).
- Source deploy IAM errors: grant Cloud Build SA permission to act as the runtime service account.
- Inspect before overwrite: `gcloud run services list`.

## Vertex AI

- Missing project/location → fallback explanations (`source: fallback`).
- Permission denied → grant `roles/aiplatform.user` to runtime SA.
- Timeouts → increase `AI_TIMEOUT` only if needed; product continues without AI.

## Stale invitations / conflicts

- Accept returns 409 “stale” → refresh matches; suggested quantity exceeded remaining/capacity.
- Duplicate accept → 409 already accepted/cancelled.
- After partial accept, offers rebalance; sums of **pending** suggestions ≤ remaining stock.
