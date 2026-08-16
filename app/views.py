from datetime import datetime, timezone

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import func

from . import db
from .forms import HeightForm, UpdateForm, WeightForm, WorkoutForm
from .models import Exercise, ExerciseSet, Height, SessionExercise, User, Weight, Workout, WorkoutSession


views = Blueprint("views", __name__)


def json_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


def owned_session(session_id):
    session = db.session.scalar(
        db.select(WorkoutSession).where(
            WorkoutSession.id == session_id,
            WorkoutSession.user_id == current_user.id,
        )
    )
    if session is None:
        abort(404)
    return session


@views.route("/landing")
def landing():
    return render_template("landing.html", user=current_user)


@views.route("/")
@login_required
def dashboard():
    workouts = db.session.scalars(
        db.select(Workout).where(Workout.creator_id == current_user.id).order_by(Workout.name)
    ).all()
    sessions = db.session.scalars(
        db.select(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id)
        .order_by(WorkoutSession.start_time.desc())
    ).all()
    for session in sessions:
        session.total_sets = sum(len(item.sets) for item in session.session_exercises)
    return render_template("dashboard.html", user=current_user, workouts=workouts, recent_sessions=sessions)


@views.route("/exercise")
@login_required
def exercise_library():
    exercises = db.session.scalars(db.select(Exercise).order_by(Exercise.name)).all()
    return render_template("exercise.html", exercises=exercises, user=current_user)


@views.route("/exercises")
@login_required
def get_all_exercises():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    result = db.paginate(db.select(Exercise).order_by(Exercise.name), page=page, per_page=per_page, error_out=False)
    return jsonify(
        exercises=[
            {
                "id": item.id,
                "name": item.name,
                "target": item.target,
                "secondaryMuscles": item.secondary_muscles,
                "instructions": item.instructions,
                "gifUrl": item.image_url,
            }
            for item in result.items
        ],
        total=result.total,
        pages=result.pages,
        current_page=result.page,
    )


@views.route("/create_workout", methods=["GET", "POST"])
@login_required
def create_workout():
    form = WorkoutForm()
    exercises = db.session.scalars(db.select(Exercise).order_by(Exercise.name)).all()
    form.exercises.choices = [(item.id, item.name) for item in exercises]
    if form.validate_on_submit():
        selected = db.session.scalars(db.select(Exercise).where(Exercise.id.in_(form.exercises.data))).all()
        if len(selected) != len(set(form.exercises.data)):
            abort(400)
        workout = Workout(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            creator=current_user,
            exercises=list(selected),
        )
        db.session.add(workout)
        db.session.commit()
        flash("Routine created.", "success")
        return redirect(url_for("views.dashboard"))
    return render_template("create_workout.html", form=form, user=current_user)


@views.route("/delete_workout", methods=["POST"])
@login_required
def delete_workout():
    data = json_payload()
    workout = db.session.scalar(
        db.select(Workout).where(Workout.id == data.get("workoutId"), Workout.creator_id == current_user.id)
    )
    if workout is None:
        abort(404)
    db.session.delete(workout)
    db.session.commit()
    return jsonify(success=True)


@views.route("/profile-info", methods=["GET", "POST"])
@login_required
def profile_info():
    form = UpdateForm(obj=current_user)
    if form.validate_on_submit():
        username = form.username.data.strip()
        conflict = db.session.scalar(
            db.select(User).where(func.lower(User.username) == username.lower(), User.id != current_user.id)
        )
        if conflict:
            form.username.errors.append("That username is already taken.")
        else:
            current_user.first_name = form.first_name.data.strip()
            current_user.username = username
            current_user.birthdate = form.birthdate.data
            current_user.gender = form.gender.data or None
            current_user.city = form.city.data.strip() if form.city.data else None
            current_user.county = form.county.data.strip() if form.county.data else None
            current_user.country = form.country.data.strip() if form.country.data else None
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("views.profile_info"))
    return render_template("profile_info.html", user=current_user, form=form)


@views.route("/faq")
def faq():
    return render_template("faq.html", user=current_user)


@views.route("/tracking")
@login_required
def tracking():
    workouts = db.session.scalars(
        db.select(Workout).where(Workout.creator_id == current_user.id).order_by(Workout.name)
    ).all()
    exercises = db.session.scalars(db.select(Exercise).order_by(Exercise.name)).all()
    recent_sessions = db.session.scalars(
        db.select(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id)
        .order_by(WorkoutSession.start_time.desc())
        .limit(10)
    ).all()
    routine_id = request.args.get("routine_id", type=int)
    if routine_id and not any(item.id == routine_id for item in workouts):
        abort(404)
    return render_template(
        "tracking.html",
        user=current_user,
        workouts=workouts,
        exercises=exercises,
        recent_sessions=recent_sessions,
        requested_routine_id=routine_id,
    )


@views.route("/start_empty_workout", methods=["POST"])
@login_required
def start_empty_workout():
    data = request.get_json(silent=True) or {}
    routine_id = data.get("workout_id")
    routine = None
    if routine_id:
        routine = db.session.scalar(
            db.select(Workout).where(Workout.id == routine_id, Workout.creator_id == current_user.id)
        )
        if routine is None:
            abort(404)
    session = WorkoutSession(
        user=current_user,
        workout=routine,
        notes=routine.name if routine else "Custom Workout",
    )
    db.session.add(session)
    db.session.flush()
    if routine:
        for order, exercise in enumerate(routine.exercises, start=1):
            session.session_exercises.append(SessionExercise(exercise=exercise, order=order))
    db.session.commit()
    return jsonify(
        success=True,
        session_id=session.id,
        workout_name=session.notes,
        exercises=[
            {"id": item.exercise.id, "name": item.exercise.name, "target": item.exercise.target, "gifUrl": item.exercise.image_url}
            for item in session.session_exercises
        ],
    )


@views.route("/add_session_exercise", methods=["POST"])
@login_required
def add_session_exercise():
    data = json_payload()
    session = owned_session(data.get("session_id"))
    exercise = db.session.get(Exercise, data.get("exercise_id"))
    if exercise is None or any(item.exercise_id == exercise.id for item in session.session_exercises):
        abort(400)
    item = SessionExercise(workout_session=session, exercise=exercise, order=len(session.session_exercises) + 1)
    db.session.add(item)
    db.session.commit()
    return jsonify(success=True, message="Exercise added to session.")


@views.route("/remove_session_exercise", methods=["POST"])
@login_required
def remove_session_exercise():
    data = json_payload()
    session = owned_session(data.get("session_id"))
    item = db.session.scalar(
        db.select(SessionExercise).where(
            SessionExercise.workout_session_id == session.id,
            SessionExercise.exercise_id == data.get("exercise_id"),
        )
    )
    if item is None:
        abort(404)
    db.session.delete(item)
    db.session.commit()
    return jsonify(success=True, message="Exercise removed from session.")


@views.route("/add_exercise_set", methods=["POST"])
@login_required
def add_exercise_set():
    data = json_payload()
    session = owned_session(data.get("session_id"))
    item = db.session.scalar(
        db.select(SessionExercise).where(
            SessionExercise.workout_session_id == session.id,
            SessionExercise.exercise_id == data.get("exercise_id"),
        )
    )
    if item is None:
        abort(404)
    try:
        reps = int(data.get("reps"))
        set_number = int(data.get("set_number"))
        weight = float(data["weight"]) if data.get("weight") not in (None, "") else None
    except (TypeError, ValueError):
        abort(400)
    if reps < 1 or set_number < 1 or (weight is not None and weight < 0):
        abort(400)
    exercise_set = ExerciseSet(
        session_exercise=item,
        set_number=set_number,
        reps=reps,
        weight=weight,
        rest_time=data.get("rest_time"),
        is_completed=True,
    )
    db.session.add(exercise_set)
    db.session.commit()
    return jsonify(success=True, message="Set saved.")


@views.route("/end_workout_session", methods=["POST"])
@login_required
def end_workout_session():
    data = json_payload()
    session = owned_session(data.get("session_id"))
    session.notes = (data.get("workout_name") or session.notes or "Custom Workout").strip()[:200]
    session.end_time = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(success=True, status="success", message="Workout saved.")


@views.route("/discard_workout_session", methods=["POST"])
@login_required
def discard_workout_session():
    session = owned_session(json_payload().get("session_id"))
    db.session.delete(session)
    db.session.commit()
    return jsonify(success=True)


@views.route("/delete_session", methods=["POST"])
@login_required
def delete_session():
    session = owned_session(json_payload().get("sessionId"))
    db.session.delete(session)
    db.session.commit()
    return jsonify(success=True)


@views.route("/account")
@login_required
def account():
    return render_template("account.html", user=current_user)


@views.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    user = current_user._get_current_object()
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "success")
    return redirect(url_for("views.landing"))


@views.route("/measurements", methods=["GET", "POST"])
@login_required
def measurements():
    height_form = HeightForm(prefix="height")
    weight_form = WeightForm(prefix="weight")
    if height_form.submit.data and height_form.validate_on_submit():
        record = db.session.scalar(
            db.select(Height).where(Height.user_id == current_user.id, Height.date == height_form.date.data)
        )
        if record:
            record.height = height_form.height.data
        else:
            db.session.add(Height(user=current_user, height=height_form.height.data, date=height_form.date.data))
        db.session.commit()
        return redirect(url_for("views.measurements"))
    if weight_form.submit.data and weight_form.validate_on_submit():
        record = db.session.scalar(
            db.select(Weight).where(Weight.user_id == current_user.id, Weight.date == weight_form.date.data)
        )
        if record:
            record.weight = weight_form.weight.data
        else:
            db.session.add(Weight(user=current_user, weight=weight_form.weight.data, date=weight_form.date.data))
        db.session.commit()
        return redirect(url_for("views.measurements"))

    height_rows = db.session.execute(
        db.select(Height.height, Height.date).where(Height.user_id == current_user.id).order_by(Height.date)
    ).all()
    weight_rows = db.session.execute(
        db.select(Weight.weight, Weight.date).where(Weight.user_id == current_user.id).order_by(Weight.date)
    ).all()
    heights = [value for value, _ in height_rows]
    height_dates = [date.strftime("%d %b %y") for _, date in height_rows]
    weights = [value for value, _ in weight_rows]
    weight_dates = [date.strftime("%d %b %y") for _, date in weight_rows]
    return render_template(
        "measurements.html",
        user=current_user,
        heightForm=height_form,
        weightForm=weight_form,
        height_data=list(zip(heights, height_dates)),
        weight_data=list(zip(weights, weight_dates)),
        heights=heights,
        height_dates=height_dates,
        weights=weights,
        weight_dates=weight_dates,
    )
