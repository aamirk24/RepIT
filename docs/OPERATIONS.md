# Operations runbook

## Routine release

1. Confirm CI is green and review dependency-audit output.
2. Confirm any new model change has a committed Alembic migration and one migration head.
3. Deploy the reviewed commit through Render.
4. Watch startup logs for `deployment_preparation_complete` and the expected exercise counts.
5. Check `/health/ready`, then complete the release smoke test in `DEPLOYMENT.md`.

The release identifier is Render's commit SHA. Every dynamic response also carries `X-Request-ID`; use it to correlate a user-visible failure with structured application logs.

## Incident triage

1. Check Render service health and recent deploy status.
2. Call `/health`; if it fails, inspect process startup and Gunicorn logs.
3. Call `/health/ready`; if only readiness fails, inspect Neon status, connection limits, credentials, and database availability.
4. Search logs by request ID and status code. RepIT deliberately excludes query strings, request bodies, cookies, and client IP addresses from application access logs.
5. If the newest release caused the incident, roll back to the last known-good Render deploy. Do not reverse a database migration blindly; first determine whether the older code is compatible with the current schema.

## Database change rules

- Prefer additive, backward-compatible migrations.
- Never edit a migration that has reached production.
- Test both a fresh migration chain and an upgrade from a realistic backup before a destructive schema change.
- Keep catalogue synchronisation idempotent and provider history independent.
- Take and verify a backup before dropping or rewriting columns or rows.

## Secret rotation

- `DATABASE_URL`: create or rotate the Neon credential, update Render, redeploy, then revoke the old credential after health checks pass.
- `SECRET_KEY`: changing it invalidates all existing login and CSRF sessions. Rotate during a controlled release and announce the forced sign-in if users exist.
- `SENTRY_DSN`: replace it in Render and redeploy; never place it in client-side code.

## Monitoring baseline

Alert or investigate when readiness fails, HTTP 5xx responses rise, requests repeatedly exceed the 30-second worker timeout, deploy preparation fails, database connections are exhausted, or storage approaches its plan limit. Sentry is optional; when enabled, keep default PII disabled and use a minimal trace sample rate.

## Catalogue maintenance

Free Exercise DB is a commit-pinned repository snapshot, not a runtime API. Updating it requires a reviewed source commit, licence/schema review, checksum update, catalogue regression tests, and a normal application release. Never silently pull unpinned catalogue content during deploy.
