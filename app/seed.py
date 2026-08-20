import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from . import db
from .models import Exercise


FREE_EXERCISE_DB_COMMIT = "b0eed061e1c832b3ed815fbaa4b45b3cdc14df49"
FREE_EXERCISE_DB_SHA256 = "d68a817484964095e6af0be2cdcbcc2c2504168d1d190c7d5c725ce52f3ae1f4"
CATALOG_VERSION = FREE_EXERCISE_DB_COMMIT[:12]
CATALOG_SOURCE = "free-exercise-db"
DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "free-exercise-db" / "exercises.json"
REPOSITORY_URL = "https://github.com/yuhonas/free-exercise-db"
RAW_MEDIA_ROOT = (
    f"https://raw.githubusercontent.com/yuhonas/free-exercise-db/{FREE_EXERCISE_DB_COMMIT}/exercises"
)
LICENSE_URL = (
    f"https://github.com/yuhonas/free-exercise-db/blob/{FREE_EXERCISE_DB_COMMIT}/LICENSE.md"
)


@dataclass(frozen=True)
class CatalogSeedResult:
    created: int
    updated: int
    retired: int = 0


class ExerciseCatalogProvider(Protocol):
    source: str

    def records(self) -> Iterable[dict]: ...


def slug_from_provider_id(provider_id):
    return provider_id.lower().replace("_", "-")


class FreeExerciseDbProvider:
    """Load a verified, pinned public-domain Free Exercise DB snapshot."""

    source = CATALOG_SOURCE

    def __init__(self, dataset_path=DATASET_PATH):
        self.dataset_path = Path(dataset_path)

    def records(self):
        payload = self.dataset_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != FREE_EXERCISE_DB_SHA256:
            raise RuntimeError("Free Exercise DB snapshot checksum does not match the pinned release.")
        for item in json.loads(payload):
            images = [f"{RAW_MEDIA_ROOT}/{quote(path, safe='/')}" for path in item["images"]]
            primary = item["primaryMuscles"]
            instructions = item["instructions"]
            yield {
                "slug": slug_from_provider_id(item["id"]),
                "name": item["name"],
                "description": instructions[0] if instructions else f"Exercise guidance for {item['name']}.",
                "body_part": primary[0],
                "target": primary[0],
                "equipment": item["equipment"] or "none",
                "difficulty": item["level"],
                "category": item["category"],
                "secondary_muscles": item["secondaryMuscles"],
                "instructions": instructions,
                "image_url": images[0],
                "image_urls": images,
                "source": self.source,
                "source_identifier": item["id"],
                "source_url": f"{REPOSITORY_URL}/blob/{FREE_EXERCISE_DB_COMMIT}/exercises/{quote(item['id'])}.json",
                "license_name": "The Unlicense",
                "license_url": LICENSE_URL,
                "attribution_text": "Exercise data and images from Free Exercise DB (public domain).",
                "catalog_version": CATALOG_VERSION,
                "is_active": True,
            }


def seed_exercises(provider: ExerciseCatalogProvider | None = None):
    provider = provider or FreeExerciseDbProvider()
    records = list(provider.records())
    existing = db.session.scalars(db.select(Exercise)).all()
    by_provider_key = {
        (item.source, item.source_identifier): item for item in existing if item.source_identifier
    }
    by_name = {item.name.casefold(): item for item in existing}
    seen_ids = set()
    created = 0
    updated = 0

    for data in records:
        if data["source"] != provider.source:
            raise ValueError("Catalogue record source does not match its provider.")
        key = (data["source"], data["source_identifier"])
        record = by_provider_key.get(key)
        if record is None:
            # Re-home an exact scaffold match so routines and history retain their foreign keys.
            record = by_name.get(data["name"].casefold())
        if record is None:
            record = Exercise(**data)
            db.session.add(record)
            created += 1
        else:
            changed = False
            for field, value in data.items():
                if getattr(record, field) != value:
                    setattr(record, field, value)
                    changed = True
            if changed:
                updated += 1
        db.session.flush()
        seen_ids.add(record.id)

    retired = 0
    for record in existing:
        if record.id in seen_ids:
            continue
        if record.source == provider.source:
            if record.is_active:
                record.is_active = False
                retired += 1
            continue
        if record.source == "RepIT":
            is_referenced = bool(record.workouts or record.session_exercises)
            if is_referenced:
                record.is_active = False
                record.attribution_text = "Legacy RepIT scaffold retained for existing workout history."
            else:
                db.session.delete(record)
            retired += 1

    db.session.commit()
    return CatalogSeedResult(created=created, updated=updated, retired=retired)
