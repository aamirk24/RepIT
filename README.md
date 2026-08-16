# RepIT Fitness Tracker

RepIT is a Flask fitness tracker for creating reusable routines, logging workout sessions and sets, browsing an offline exercise library, and charting body measurements.

This repository is currently in **Stage 0 restoration**. The original PythonAnywhere deployment and ExerciseDB integration are not active. The development catalogue contains original RepIT fixture content and the application does not make network requests at startup.

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

## Tests

```bash
python -m unittest discover -s tests -v
```

## Current features

- Account registration and session authentication
- Offline exercise library and search
- Reusable workout routines
- Custom and routine-based workout sessions
- Exercise, set, repetition, and weight logging
- Workout history
- Profile and body-measurement tracking

## Data-source note

The previous coursework version used ExerciseDB through RapidAPI. RepIT no longer bundles or caches that provider's data. A production catalogue and its attribution model will be finalised in Stage 1.
