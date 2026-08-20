# Production deployment

RepIT is prepared for a Render web service backed by Neon PostgreSQL. The repository does not create either account or provision billable infrastructure automatically.

## Before deploying

1. Create a Neon project in the same region you will use for Render.
2. Copy Neon's **pooled** connection string. RepIT uses a small application-side pool as well, so keep the default pool settings until traffic data justifies changing them.
3. In Render, create a Blueprint from this repository and review `render.yaml` before applying it.
4. Enter the pooled Neon connection string when Render requests `DATABASE_URL`. Render generates `SECRET_KEY` rather than storing it in the repository.
5. Leave `SENTRY_DSN` unset initially, or add a server-side DSN after creating a Sentry project. RepIT sends no default personally identifiable information.

The start command runs `prepare-deploy` before Gunicorn. That command holds a PostgreSQL advisory lock, applies every migration, and idempotently synchronises the pinned exercise snapshot. This allows multiple starting instances to wait for one safe database preparation rather than racing.

## Required production variables

| Variable | Purpose |
| --- | --- |
| `APP_ENV=production` | Enables strict validation and secure browser settings. |
| `SECRET_KEY` | Random secret of at least 32 characters; never reuse a development value. |
| `DATABASE_URL` | Neon pooled PostgreSQL connection string. |
| `PROXY_FIX_HOPS=1` | Trusts exactly Render's forwarding proxy for host, scheme, and client address. |

Optional settings are documented in `.env.example`. Do not add secrets to `render.yaml`, `.env.example`, logs, screenshots, or GitHub Actions.

## Release checks

Before promoting a commit:

```bash
python -m unittest discover -s tests -v
python -m compileall -q app migrations tests
python -m flask --app main db heads
```

GitHub Actions repeats those checks and audits production dependencies. Render is configured to deploy only after those checks pass.

After deployment, verify:

- `/health` responds with `status: ok` and the release version.
- `/health/ready` responds with `status: ready` and therefore confirms database access.
- Signup, login, exercise search, routine creation, workout completion, progress charts, unit preferences, and account deletion work from a clean browser session.
- Logs contain request IDs but do not contain passwords, cookies, form bodies, or database URLs.

## Free-tier expectations

Render's free web service can sleep after inactivity and take about a minute to wake. This is acceptable for an initial portfolio deployment but not a production service-level commitment. Render's filesystem is ephemeral; all user data must remain in Neon, not local files. Do not substitute Render's free PostgreSQL for Neon because the free Render database expires after 30 days.

Before inviting sustained public usage, move the web service to a non-sleeping plan and verify Neon storage, compute, backup, and connection limits against expected traffic.
