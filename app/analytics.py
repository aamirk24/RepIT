from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from . import db
from .models import ExerciseSet, SessionExercise, WorkoutSession
from .units import display_weight, weight_unit


VALID_RANGES = {30, 90, 365}


def _aware(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _start_of_day(value):
    return datetime.combine(value.date(), time.min, tzinfo=timezone.utc)


def _completed_sessions(user_id, since=None, before=None):
    query = db.select(WorkoutSession).where(
        WorkoutSession.user_id == user_id,
        WorkoutSession.end_time.is_not(None),
    )
    if since is not None:
        query = query.where(WorkoutSession.start_time >= since)
    if before is not None:
        query = query.where(WorkoutSession.start_time < before)
    return db.session.scalars(query.order_by(WorkoutSession.start_time)).all()


def _set_rows(user_id, since=None, before=None, exercise_id=None):
    query = (
        db.select(
            WorkoutSession.id.label("session_id"),
            WorkoutSession.start_time,
            SessionExercise.exercise_id,
            SessionExercise.exercise_name,
            SessionExercise.target_name,
            ExerciseSet.set_number,
            ExerciseSet.reps,
            ExerciseSet.weight,
        )
        .join(SessionExercise, SessionExercise.workout_session_id == WorkoutSession.id)
        .join(ExerciseSet, ExerciseSet.session_exercise_id == SessionExercise.id)
        .where(
            WorkoutSession.user_id == user_id,
            WorkoutSession.end_time.is_not(None),
            ExerciseSet.is_completed.is_(True),
        )
    )
    if since is not None:
        query = query.where(WorkoutSession.start_time >= since)
    if before is not None:
        query = query.where(WorkoutSession.start_time < before)
    if exercise_id is not None:
        query = query.where(SessionExercise.exercise_id == exercise_id)
    return db.session.execute(query.order_by(WorkoutSession.start_time, ExerciseSet.set_number)).all()


def _period_summary(user_id, since, before, unit_system):
    sessions = _completed_sessions(user_id, since, before)
    rows = _set_rows(user_id, since, before)
    volume_kg = sum(row.reps * row.weight for row in rows if row.weight is not None)
    duration_seconds = sum(
        max(0, (_aware(session.end_time) - _aware(session.start_time)).total_seconds()) for session in sessions
    )
    return {
        "workouts": len(sessions),
        "sets": len(rows),
        "reps": sum(row.reps for row in rows),
        "volume": display_weight(volume_kg, unit_system),
        "durationHours": round(duration_seconds / 3600, 1),
    }


def dashboard_summary(user_id, unit_system, now=None):
    now = _aware(now or datetime.now(timezone.utc))
    return _period_summary(user_id, now - timedelta(days=30), now, unit_system)


def _change(current, previous, key):
    old = previous[key]
    if old == 0:
        return None if current[key] == 0 else 100
    return round((current[key] - old) / old * 100)


def _weekly_activity(sessions, rows, now, unit_system):
    current_monday = _start_of_day(now) - timedelta(days=now.weekday())
    weeks = []
    for offset in range(11, -1, -1):
        start = current_monday - timedelta(weeks=offset)
        end = start + timedelta(days=7)
        week_sessions = {session.id for session in sessions if start <= _aware(session.start_time) < end}
        volume_kg = sum(
            row.reps * row.weight
            for row in rows
            if row.weight is not None and start <= _aware(row.start_time) < end
        )
        weeks.append(
            {
                "label": start.strftime("%d %b"),
                "workouts": len(week_sessions),
                "volume": display_weight(volume_kg, unit_system),
            }
        )
    return weeks


def _training_streak(sessions, now):
    active_weeks = {
        (_aware(session.start_time) - timedelta(days=_aware(session.start_time).weekday())).date()
        for session in sessions
    }
    week = (_start_of_day(now) - timedelta(days=now.weekday())).date()
    if week not in active_weeks:
        week -= timedelta(days=7)
    streak = 0
    while week in active_weeks:
        streak += 1
        week -= timedelta(days=7)
    return streak


def _personal_records(rows, unit_system):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.exercise_id].append(row)
    records = []
    for exercise_id, exercise_rows in grouped.items():
        weighted = [row for row in exercise_rows if row.weight is not None]
        estimated = [row for row in weighted if 1 <= row.reps <= 12]
        heaviest = max(weighted, key=lambda row: (row.weight, row.reps), default=None)
        best_e1rm = max(estimated, key=lambda row: row.weight * (1 + row.reps / 30), default=None)
        max_reps = max(exercise_rows, key=lambda row: row.reps)
        latest = max(exercise_rows, key=lambda row: _aware(row.start_time))
        records.append(
            {
                "exerciseId": exercise_id,
                "name": latest.exercise_name,
                "target": latest.target_name,
                "heaviestWeight": display_weight(heaviest.weight, unit_system) if heaviest else None,
                "estimatedOneRepMax": display_weight(
                    best_e1rm.weight * (1 + best_e1rm.reps / 30), unit_system
                )
                if best_e1rm
                else None,
                "maxReps": max_reps.reps,
                "lastPerformed": _aware(latest.start_time).date(),
            }
        )
    return sorted(records, key=lambda item: (item["lastPerformed"], item["name"]), reverse=True)


def _exercise_history(rows, unit_system):
    sessions = defaultdict(list)
    for row in rows:
        sessions[(row.session_id, _aware(row.start_time))].append(row)
    history = []
    for (session_id, started), set_rows in sessions.items():
        weighted = [row for row in set_rows if row.weight is not None]
        estimated = [row.weight * (1 + row.reps / 30) for row in weighted if row.reps <= 12]
        volume_kg = sum(row.reps * row.weight for row in weighted)
        history.append(
            {
                "sessionId": session_id,
                "date": started.date(),
                "sets": len(set_rows),
                "reps": sum(row.reps for row in set_rows),
                "volume": display_weight(volume_kg, unit_system),
                "topWeight": display_weight(max((row.weight for row in weighted), default=None), unit_system),
                "estimatedOneRepMax": display_weight(max(estimated), unit_system) if estimated else None,
            }
        )
    return sorted(history, key=lambda item: item["date"], reverse=True)


def progress_report(user_id, unit_system, range_days=90, exercise_id=None, now=None):
    now = _aware(now or datetime.now(timezone.utc))
    if range_days not in VALID_RANGES:
        range_days = 90
    period_start = _start_of_day(now) - timedelta(days=range_days - 1)
    previous_start = period_start - timedelta(days=range_days)
    current = _period_summary(user_id, period_start, now, unit_system)
    previous = _period_summary(user_id, previous_start, period_start, unit_system)

    all_sessions = _completed_sessions(user_id)
    all_rows = _set_rows(user_id)
    twelve_week_start = _start_of_day(now) - timedelta(weeks=12)
    recent_sessions = [session for session in all_sessions if _aware(session.start_time) >= twelve_week_start]
    recent_rows = [row for row in all_rows if _aware(row.start_time) >= twelve_week_start]
    records = _personal_records(all_rows, unit_system)
    exercise_ids = {record["exerciseId"] for record in records}
    if exercise_id not in exercise_ids:
        exercise_id = records[0]["exerciseId"] if records else None
    selected_record = next((record for record in records if record["exerciseId"] == exercise_id), None)
    selected_rows = [row for row in all_rows if row.exercise_id == exercise_id]
    exercise_history = _exercise_history(selected_rows, unit_system)
    recent_history = list(reversed(exercise_history[:12]))
    if any(item["estimatedOneRepMax"] is not None for item in recent_history):
        exercise_trend = [
            {"date": item["date"], "value": item["estimatedOneRepMax"]}
            for item in recent_history
            if item["estimatedOneRepMax"] is not None
        ]
        trend_label = "Estimated 1RM"
        trend_unit = weight_unit(unit_system)
    else:
        exercise_trend = [{"date": item["date"], "value": item["reps"]} for item in recent_history]
        trend_label = "Total repetitions"
        trend_unit = "reps"

    return {
        "rangeDays": range_days,
        "summary": current,
        "changes": {
            "workouts": _change(current, previous, "workouts"),
            "volume": _change(current, previous, "volume"),
        },
        "weekly": _weekly_activity(recent_sessions, recent_rows, now, unit_system),
        "streakWeeks": _training_streak(all_sessions, now),
        "records": records,
        "selectedExercise": selected_record,
        "exerciseHistory": exercise_history,
        "exerciseTrend": exercise_trend,
        "trendLabel": trend_label,
        "trendUnit": trend_unit,
        "weightUnit": weight_unit(unit_system),
    }
