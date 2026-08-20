# RepIT Fitness Tracker

RepIT is a Flask fitness tracker for creating reusable routines, logging workout sessions and sets, browsing an exercise library, and charting body measurements.

This repository has completed **Stage 6 production and operations preparation**. The original PythonAnywhere deployment and paid ExerciseDB integration are not active. RepIT uses a pinned public-domain snapshot of Free Exercise DB and makes no provider API requests at startup.

## Local setup

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
flask --app main db upgrade
flask --app main seed-exercises
flask --app main run
```

Open `http://127.0.0.1:5000` and visit `/signup` to create a local account.

## Configuration

Copy `.env.example` to `.env` and replace the development secret. `.env` and local SQLite databases are intentionally ignored.

RepIT has explicit environments selected with `APP_ENV`:

- `development`: SQLite by default, debugging enabled
- `testing`: isolated in-memory SQLite and disabled CSRF for the test client
- `production`: requires `SECRET_KEY` and `DATABASE_URL`, enables secure cookies and fails during startup if either value is missing

PostgreSQL is the production database. Standard `postgres://` and `postgresql://` provider URLs are automatically normalised to the Psycopg 3 SQLAlchemy driver.

Example production variables:

```bash
APP_ENV=production
SECRET_KEY=a-long-random-production-secret
DATABASE_URL=postgresql://user:password@host:5432/repit
```

Never commit real environment values.

## Production deployment

RepIT includes a Render Blueprint, Gunicorn configuration, managed PostgreSQL readiness check, structured request logging, optional privacy-safe Sentry integration, and a deployment command that serialises migrations and catalogue synchronisation with a PostgreSQL advisory lock.

The intended initial stack is a Render web service plus a Neon pooled PostgreSQL connection. No cloud resources are created by this repository. Follow [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) to provision and verify them manually. Operational response and recovery procedures live in [docs/OPERATIONS.md](docs/OPERATIONS.md) and [docs/BACKUP_AND_RECOVERY.md](docs/BACKUP_AND_RECOVERY.md).

Production process command:

```bash
python -m flask --app main prepare-deploy && gunicorn -c gunicorn.conf.py main:app
```

The command upgrades the schema and synchronises the pinned catalogue before accepting traffic. It is safe to repeat.

## Account security

RepIT uses CSRF protection, secure password hashing, generic login failures, persistent login throttling, explicit remember-me sessions, password-confirmed account deletion, and global session invalidation after a password change. Production responses add HTTPS-only cookies, HSTS, a content security policy, and defensive browser headers.

See [ROADMAP.md](ROADMAP.md) for completed product stages and integrations intentionally deferred until their external prerequisites are chosen. Security reporting and retention details are in [docs/SECURITY.md](docs/SECURITY.md).

## Tests

```bash
python -m unittest discover -s tests -v
```

## Current features

- Account registration and session authentication
- Exercise library and search backed by the normalized RepIT catalogue
- Exercise filtering by name, body part, equipment, difficulty, and category through the authenticated JSON endpoint
- Reusable workout routines
- Recoverable custom and routine-based workout sessions with a single active session per user
- Editable exercise sets with repetitions, weight, rest time, ordering, notes, and server-backed timers
- Immutable completed sessions and provider-independent exercise snapshots for reliable history
- Workout history
- 30/90/365-day progress summaries, comparison periods, 12-week frequency, and training streaks
- Per-exercise personal records, estimated one-repetition maximum trends, and complete exercise history
- Metric and imperial display preferences with canonical metric storage
- Profile and body-measurement tracking

## Analytics definitions

Analytics count completed sessions and completed sets only. Weighted training volume is `external load × repetitions`; bodyweight sets contribute to set and repetition totals but not weighted volume because RepIT does not invent a bodyweight load. Estimated one-repetition maximum uses the Epley formula for weighted sets of 1–12 repetitions. All weights and measurements are stored canonically in kilograms and centimetres, then converted for imperial display.

Exercise history is grouped by RepIT's internal exercise identity and uses the exercise-name, target, and equipment snapshots captured when the workout was performed. Upstream catalogue wording changes therefore do not rewrite historical analytics.

## Exercise catalogue

RepIT consumes externally maintained exercise data rather than maintaining a proprietary catalogue. Its provider contract maps source records into a normalized local `Exercise` model, keeping routines, workout sessions, search, and analytics independent from the upstream format.

The current provider is [Free Exercise DB](https://github.com/yuhonas/free-exercise-db), an open dataset released under The Unlicense/public-domain dedication. RepIT vendors a checksum-verified snapshot pinned to an exact upstream commit. It currently contains 873 exercises with instructions, difficulty, category, equipment, muscle metadata, and two demonstration images per exercise.

The seed command is an idempotent provider synchronization operation: it adds missing records, updates changed content, and deactivates removed upstream records without breaking historical workout references. Exact-name scaffold records are re-homed in place so their database IDs and relationships survive. Unreferenced handcrafted scaffold rows are removed; referenced legacy rows remain inactive only where required to preserve user data.

Exercise images are loaded from commit-pinned upstream URLs and lazy-loaded by the browser. The combined metadata snapshot and its upstream licence are stored under `data/free-exercise-db/`; update provenance and checksum details are documented in `SNAPSHOT.md`. RepIT has no exercise API key, paid catalogue dependency, or runtime catalogue quota.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for source and licence details.

## Health check

`GET /health` confirms that the application process is alive. `GET /health/ready` also verifies the database connection and is the production routing check. Both return the current release identifier and expose no secrets.
