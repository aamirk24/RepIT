# RepIT Fitness Tracker

RepIT is a Flask fitness tracker for creating reusable routines, logging workout sessions and sets, browsing an exercise library, and charting body measurements.

This repository is currently in **Stage 1 production-foundation development**. The original PythonAnywhere deployment and ExerciseDB integration are not active. Until a replacement provider and its usage terms are approved, RepIT uses a small deterministic fallback catalogue and makes no network requests at startup.

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

## Tests

```bash
python -m unittest discover -s tests -v
```

## Current features

- Account registration and session authentication
- Exercise library and search backed by the normalized RepIT catalogue
- Exercise filtering by name, body part, equipment, difficulty, and category through the authenticated JSON endpoint
- Reusable workout routines
- Custom and routine-based workout sessions
- Exercise, set, repetition, and weight logging
- Workout history
- Profile and body-measurement tracking

## Exercise catalogue

RepIT is designed to consume a licensed external exercise provider rather than maintain a complete proprietary dataset. Its provider contract maps external records into a normalized local `Exercise` model, keeping the rest of the application independent from any one API. Routines and completed sessions reference these normalized records, so provider outages do not corrupt workout history.

The current provider is a temporary bundled fallback containing 52 development records across strength, cardio, stability, mobility, and stretching. It will be replaced after a provider's commercial-use, caching, GIF-embedding, attribution, and post-cancellation terms are confirmed.

The seed command is an idempotent provider synchronization operation: it adds missing records and updates changed content without duplicating exercises or deleting records belonging to another source. Every record retains a provider identifier, source, version, attribution, and optional licence metadata. Automated tests can supply an in-memory provider without making paid API requests.

The previous coursework version used ExerciseDB through RapidAPI. RepIT does not bundle, cache, or request that provider's data. A future adapter may retrieve metadata and GIF URLs only within its provider's confirmed terms; API credentials will remain server-side and outside Git.

## Health check

`GET /health` returns a small status response suitable for local and future deployment health checks. It does not query external services.
