from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from . import db
from .models import Exercise, ExerciseSet, SessionExercise, Workout, WorkoutSession
from .units import display_weight, stored_weight, weight_unit


class WorkoutError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class StartedWorkout:
    session: WorkoutSession
    created: bool


def active_session_for(user_id):
    return db.session.scalar(
        db.select(WorkoutSession).where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.end_time.is_(None),
        )
    )


def owned_session(user_id, session_id, *, active_only=False):
    try:
        session_id = int(session_id)
    except (TypeError, ValueError):
        raise WorkoutError("Workout session not found.", 404) from None
    query = db.select(WorkoutSession).where(
        WorkoutSession.id == session_id,
        WorkoutSession.user_id == user_id,
    )
    if active_only:
        query = query.where(WorkoutSession.end_time.is_(None))
    session = db.session.scalar(query)
    if session is None:
        raise WorkoutError("Workout session not found.", 404)
    return session


def _snapshot(exercise, order):
    return SessionExercise(
        exercise=exercise,
        order=order,
        exercise_name=exercise.name,
        target_name=exercise.target,
        equipment_name=exercise.equipment,
    )


def _integer(value, label):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise WorkoutError(f"{label} is invalid.") from None


def start_workout(user, routine_id=None):
    existing = active_session_for(user.id)
    if existing:
        return StartedWorkout(existing, False)

    routine = None
    if routine_id not in (None, ""):
        try:
            routine_id = int(routine_id)
        except (TypeError, ValueError):
            raise WorkoutError("Routine not found.", 404) from None
        routine = db.session.scalar(
            db.select(Workout).where(Workout.id == routine_id, Workout.creator_id == user.id)
        )
        if routine is None:
            raise WorkoutError("Routine not found.", 404)

    session = WorkoutSession(
        user=user,
        workout=routine,
        name=routine.name if routine else "Custom Workout",
    )
    db.session.add(session)
    for order, exercise in enumerate(routine.exercises if routine else (), start=1):
        session.session_exercises.append(_snapshot(exercise, order))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = active_session_for(user.id)
        if existing:
            return StartedWorkout(existing, False)
        raise
    return StartedWorkout(session, True)


def add_exercise(session, exercise_id):
    exercise_id = _integer(exercise_id, "Exercise")
    exercise = db.session.scalar(
        db.select(Exercise).where(Exercise.id == exercise_id, Exercise.is_active.is_(True))
    )
    if exercise is None:
        raise WorkoutError("Exercise not found.", 404)
    if any(item.exercise_id == exercise.id for item in session.session_exercises):
        raise WorkoutError("That exercise is already in this workout.", 409)
    item = _snapshot(exercise, len(session.session_exercises) + 1)
    session.session_exercises.append(item)
    db.session.commit()
    return item


def remove_exercise(session, exercise_id):
    exercise_id = _integer(exercise_id, "Exercise")
    item = next((item for item in session.session_exercises if item.exercise_id == exercise_id), None)
    if item is None:
        raise WorkoutError("Exercise not found in this workout.", 404)
    removed_order = item.order
    db.session.delete(item)
    db.session.flush()
    remaining_items = [
        remaining for remaining in session.session_exercises if remaining is not item and remaining.order > removed_order
    ]
    offset = len(session.session_exercises) + 1
    for remaining in remaining_items:
        remaining.order += offset
    db.session.flush()
    for remaining in remaining_items:
        remaining.order -= offset + 1
    db.session.commit()


def reorder_exercises(session, exercise_ids):
    try:
        exercise_ids = [int(value) for value in exercise_ids]
    except (TypeError, ValueError):
        raise WorkoutError("Exercise order is invalid.") from None
    current = {item.exercise_id: item for item in session.session_exercises}
    if len(exercise_ids) != len(set(exercise_ids)) or set(exercise_ids) != set(current):
        raise WorkoutError("Exercise order must contain every workout exercise exactly once.")
    offset = len(exercise_ids)
    for index, exercise_id in enumerate(exercise_ids, start=1):
        current[exercise_id].order = offset + index
    db.session.flush()
    for index, exercise_id in enumerate(exercise_ids, start=1):
        current[exercise_id].order = index
    db.session.commit()


def save_set(session, exercise_id, set_number, reps, weight=None, rest_time=None, unit_system="metric"):
    exercise_id = _integer(exercise_id, "Exercise")
    item = next((item for item in session.session_exercises if item.exercise_id == exercise_id), None)
    if item is None:
        raise WorkoutError("Exercise not found in this workout.", 404)
    try:
        set_number = int(set_number)
        reps = int(reps)
        weight = stored_weight(float(weight), unit_system) if weight not in (None, "") else None
        rest_time = int(rest_time) if rest_time not in (None, "") else None
    except (TypeError, ValueError):
        raise WorkoutError("Set values must be valid numbers.") from None
    if set_number < 1 or reps < 1 or (weight is not None and weight < 0) or (rest_time is not None and rest_time < 0):
        raise WorkoutError("Set values are outside the allowed range.")
    record = db.session.scalar(
        db.select(ExerciseSet).where(
            ExerciseSet.session_exercise_id == item.id,
            ExerciseSet.set_number == set_number,
        )
    )
    if record is None:
        record = ExerciseSet(session_exercise=item, set_number=set_number)
        db.session.add(record)
    record.reps = reps
    record.weight = weight
    record.rest_time = rest_time
    record.is_completed = True
    db.session.commit()
    return record


def delete_set(session, exercise_id, set_number):
    exercise_id = _integer(exercise_id, "Exercise")
    set_number = _integer(set_number, "Set number")
    item = next((item for item in session.session_exercises if item.exercise_id == exercise_id), None)
    if item is None:
        raise WorkoutError("Exercise not found in this workout.", 404)
    record = next((record for record in item.sets if record.set_number == set_number), None)
    if record is None:
        raise WorkoutError("Set not found.", 404)
    db.session.delete(record)
    db.session.flush()
    remaining_sets = [remaining for remaining in item.sets if remaining is not record and remaining.set_number > set_number]
    offset = len(item.sets) + 1
    for remaining in remaining_sets:
        remaining.set_number += offset
    db.session.flush()
    for remaining in remaining_sets:
        remaining.set_number -= offset + 1
    db.session.commit()


def _set_workout_details(session, name, notes):
    name = (name or "").strip()
    notes = (notes or "").strip()
    if not name or len(name) > 150 or len(notes) > 2000:
        raise WorkoutError("Workout name or notes are invalid.")
    session.name = name
    session.notes = notes or None


def update_workout(session, name, notes):
    _set_workout_details(session, name, notes)
    db.session.commit()


def complete_workout(session, name=None, notes=None):
    if not any(record.is_completed for item in session.session_exercises for record in item.sets):
        raise WorkoutError("Log at least one completed set before finishing the workout.", 409)
    _set_workout_details(session, name or session.name, notes if notes is not None else session.notes)
    session.end_time = datetime.now(timezone.utc)
    db.session.commit()


def _utc_iso(value):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def session_payload(session, unit_system="metric"):
    return {
        "id": session.id,
        "name": session.name,
        "notes": session.notes or "",
        "startTime": _utc_iso(session.start_time),
        "endTime": _utc_iso(session.end_time) if session.end_time else None,
        "weightUnit": weight_unit(unit_system),
        "exercises": [
            {
                "id": item.exercise_id,
                "sessionExerciseId": item.id,
                "name": item.exercise_name,
                "target": item.target_name,
                "equipment": item.equipment_name,
                "imageUrl": item.exercise.image_url,
                "order": item.order,
                "sets": [
                    {
                        "id": record.id,
                        "setNumber": record.set_number,
                        "reps": record.reps,
                        "weight": display_weight(record.weight, unit_system),
                        "restTime": record.rest_time,
                        "completed": record.is_completed,
                    }
                    for record in item.sets
                ],
            }
            for item in session.session_exercises
        ],
    }
