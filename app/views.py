from datetime import datetime, timezone

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from . import db
from .analytics import dashboard_summary, progress_report
from .forms import ChangePasswordForm, DeleteAccountForm, HeightForm, UpdateForm, WeightForm, WorkoutForm
from .models import Exercise, Height, User, Weight, Workout, WorkoutSession
from .units import display_height, display_weight, height_unit, stored_height, stored_weight, weight_unit
from .workouts import (
    WorkoutError,
    active_session_for,
    add_exercise,
    complete_workout,
    delete_set as delete_workout_set,
    owned_session,
    remove_exercise,
    reorder_exercises,
    save_set,
    session_payload,
    start_workout,
    update_workout,
)


views = Blueprint("views", __name__)


def json_payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    return data


@views.errorhandler(WorkoutError)
def handle_workout_error(error):
    return jsonify(success=False, error=str(error)), error.status_code


@views.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("views.dashboard"))
    return render_template("landing.html", user=current_user)


@views.route("/dashboard")
@login_required
def dashboard():
    workouts = db.session.scalars(
        db.select(Workout).where(Workout.creator_id == current_user.id).order_by(Workout.name)
    ).all()
    sessions = db.session.scalars(
        db.select(WorkoutSession)
        .where(WorkoutSession.user_id == current_user.id, WorkoutSession.end_time.is_not(None))
        .order_by(WorkoutSession.start_time.desc())
    ).all()
    for session in sessions:
        session.total_sets = sum(len(item.sets) for item in session.session_exercises)
        session.total_reps = sum(record.reps for item in session.session_exercises for record in item.sets)
        session.duration_minutes = max(0, round((session.end_time - session.start_time).total_seconds() / 60))
    return render_template(
        "dashboard.html",
        user=current_user,
        workouts=workouts,
        recent_sessions=sessions,
        active_session=active_session_for(current_user.id),
        summary=dashboard_summary(current_user.id, current_user.unit_system),
        display_weight=display_weight,
        weight_unit=weight_unit(current_user.unit_system),
        unit_system=current_user.unit_system,
    )


@views.route("/history/<int:session_id>")
@login_required
def workout_history_detail(session_id):
    session = owned_session(current_user.id, session_id)
    if session.end_time is None:
        return redirect(url_for("views.tracking"))
    total_sets = sum(len(item.sets) for item in session.session_exercises)
    total_reps = sum(record.reps for item in session.session_exercises for record in item.sets)
    volume_kg = sum(
        record.reps * record.weight
        for item in session.session_exercises
        for record in item.sets
        if record.weight is not None
    )
    duration_minutes = round((session.end_time - session.start_time).total_seconds() / 60)
    return render_template(
        "workout_history_detail.html",
        user=current_user,
        session=session,
        total_sets=total_sets,
        total_reps=total_reps,
        volume=display_weight(volume_kg, current_user.unit_system),
        weight_unit=weight_unit(current_user.unit_system),
        unit_system=current_user.unit_system,
        display_weight=display_weight,
        duration_minutes=duration_minutes,
    )


@views.route("/exercise")
@login_required
def exercise_library():
    page = max(request.args.get("page", 1, type=int), 1)
    query = db.select(Exercise).where(Exercise.is_active.is_(True))
    search = request.args.get("q", "").strip()
    if search:
        query = query.where(Exercise.name.ilike(f"%{search}%"))
    for field in ("body_part", "equipment", "difficulty"):
        value = request.args.get(field, "").strip().lower()
        if value:
            query = query.where(getattr(Exercise, field) == value)
    pagination = db.paginate(query.order_by(Exercise.name), page=page, per_page=24, error_out=False)
    facets = {}
    for field in ("body_part", "equipment", "difficulty"):
        facets[field] = db.session.scalars(
            db.select(getattr(Exercise, field))
            .where(Exercise.is_active.is_(True))
            .distinct()
            .order_by(getattr(Exercise, field))
        ).all()
    return render_template(
        "exercise.html",
        exercises=pagination.items,
        pagination=pagination,
        facets=facets,
        filters=request.args,
        user=current_user,
    )


@views.route("/exercise/<int:exercise_id>")
@login_required
def exercise_detail(exercise_id):
    exercise = db.session.scalar(
        db.select(Exercise).where(Exercise.id == exercise_id, Exercise.is_active.is_(True))
    )
    if exercise is None:
        abort(404)
    return render_template("exercise_detail.html", exercise=exercise, user=current_user)


@views.route("/exercises")
@login_required
def get_all_exercises():
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 100)
    query = db.select(Exercise).where(Exercise.is_active.is_(True))
    search = request.args.get("q", "").strip()
    if search:
        query = query.where(Exercise.name.ilike(f"%{search}%"))
    for field in ("body_part", "equipment", "difficulty", "category"):
        value = request.args.get(field, "").strip().lower()
        if value:
            query = query.where(getattr(Exercise, field) == value)
    result = db.paginate(query.order_by(Exercise.name), page=page, per_page=per_page, error_out=False)
    return jsonify(
        exercises=[
            {
                "id": item.id,
                "name": item.name,
                "slug": item.slug,
                "description": item.description,
                "bodyPart": item.body_part,
                "target": item.target,
                "equipment": item.equipment,
                "difficulty": item.difficulty,
                "category": item.category,
                "secondaryMuscles": item.secondary_muscles,
                "instructions": item.instructions,
                "gifUrl": item.image_url,
                "imageUrls": item.image_urls,
                "source": item.source,
                "attribution": item.attribution_text,
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
    exercises = db.session.scalars(
        db.select(Exercise).where(Exercise.is_active.is_(True)).order_by(Exercise.name)
    ).all()
    form.exercises.choices = [(item.id, item.name) for item in exercises]
    if form.validate_on_submit():
        selected = db.session.scalars(
            db.select(Exercise).where(Exercise.id.in_(form.exercises.data), Exercise.is_active.is_(True))
        ).all()
        if len(selected) != len(set(form.exercises.data)):
            abort(400)
        selected_by_id = {item.id: item for item in selected}
        workout = Workout(
            name=form.name.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            creator=current_user,
            exercises=[selected_by_id[exercise_id] for exercise_id in form.exercises.data],
        )
        db.session.add(workout)
        db.session.commit()
        flash("Routine created.", "success")
        return redirect(url_for("views.dashboard"))
    exercises_by_id = {item.id: item for item in exercises}
    selected_exercises = [
        exercises_by_id[exercise_id]
        for exercise_id in (form.exercises.data or [])
        if exercise_id in exercises_by_id
    ]
    return render_template(
        "create_workout.html",
        form=form,
        user=current_user,
        workout=None,
        selected_exercises=[
            {
                "id": item.id,
                "name": item.name,
                "target": item.target,
                "equipment": item.equipment,
                "imageUrls": item.image_urls,
            }
            for item in selected_exercises
        ],
    )


@views.route("/routine/<int:workout_id>", methods=["GET", "POST"])
@login_required
def edit_workout(workout_id):
    workout = db.session.scalar(
        db.select(Workout).where(Workout.id == workout_id, Workout.creator_id == current_user.id)
    )
    if workout is None:
        abort(404)
    form = WorkoutForm()
    exercises = db.session.scalars(
        db.select(Exercise).where(Exercise.is_active.is_(True)).order_by(Exercise.name)
    ).all()
    form.exercises.choices = [(item.id, item.name) for item in exercises]
    if request.method == "GET":
        form.name.data = workout.name
        form.description.data = workout.description
        form.exercises.data = [item.id for item in workout.exercises]
    if form.validate_on_submit():
        exercises_by_id = {item.id: item for item in exercises}
        if any(exercise_id not in exercises_by_id for exercise_id in form.exercises.data):
            abort(400)
        workout.name = form.name.data.strip()
        workout.description = form.description.data.strip() if form.description.data else None
        workout.exercises = [exercises_by_id[exercise_id] for exercise_id in form.exercises.data]
        db.session.commit()
        flash("Routine updated.", "success")
        return redirect(url_for("views.edit_workout", workout_id=workout.id))
    exercises_by_id = {item.id: item for item in exercises}
    selected_exercises = [
        exercises_by_id[exercise_id]
        for exercise_id in (form.exercises.data or [])
        if exercise_id in exercises_by_id
    ]
    return render_template(
        "create_workout.html",
        form=form,
        user=current_user,
        workout=workout,
        selected_exercises=[
            {"id": item.id, "name": item.name, "target": item.target, "equipment": item.equipment, "imageUrls": item.image_urls}
            for item in selected_exercises
        ],
    )


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
            current_user.unit_system = form.unit_system.data
            db.session.commit()
            flash("Profile updated.", "success")
            return redirect(url_for("views.profile_info"))
    return render_template("profile_info.html", user=current_user, form=form)


@views.route("/faq")
def faq():
    return render_template("faq.html", user=current_user)


@views.route("/privacy")
def privacy():
    return render_template("legal.html", user=current_user, document="privacy")


@views.route("/terms")
def terms():
    return render_template("legal.html", user=current_user, document="terms")


@views.route("/fitness-disclaimer")
def fitness_disclaimer():
    return render_template("legal.html", user=current_user, document="disclaimer")


@views.route("/progress")
@login_required
def progress():
    range_days = request.args.get("range", 90, type=int)
    exercise_id = request.args.get("exercise_id", type=int)
    report = progress_report(current_user.id, current_user.unit_system, range_days, exercise_id)
    exercise_name = request.args.get("exercise", "").strip().casefold()
    if exercise_name and report["records"]:
        match = next((item for item in report["records"] if item["name"].casefold() == exercise_name), None)
        if match is None:
            match = next((item for item in report["records"] if exercise_name in item["name"].casefold()), None)
        if match and match["exerciseId"] != exercise_id:
            report = progress_report(current_user.id, current_user.unit_system, range_days, match["exerciseId"])
    return render_template("progress.html", user=current_user, report=report)


@views.route("/tracking")
@login_required
def tracking():
    workouts = db.session.scalars(
        db.select(Workout).where(Workout.creator_id == current_user.id).order_by(Workout.name)
    ).all()
    routine_id = request.args.get("routine_id", type=int)
    if routine_id and not any(item.id == routine_id for item in workouts):
        abort(404)
    active_session = active_session_for(current_user.id)
    return render_template(
        "tracking.html",
        user=current_user,
        workouts=workouts,
        requested_routine_id=routine_id,
        active_session_payload=session_payload(active_session, current_user.unit_system) if active_session else None,
        weight_unit=weight_unit(current_user.unit_system),
    )


@views.route("/start_empty_workout", methods=["POST"])
@login_required
def start_empty_workout():
    data = request.get_json(silent=True) or {}
    result = start_workout(current_user, data.get("workout_id"))
    payload = session_payload(result.session, current_user.unit_system)
    return jsonify(
        success=True,
        created=result.created,
        session=payload,
        session_id=result.session.id,
        exercises=payload["exercises"],
    )


@views.route("/add_session_exercise", methods=["POST"])
@login_required
def add_session_exercise():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    item = add_exercise(session, data.get("exercise_id"))
    return jsonify(
        success=True,
        exercise=session_payload(session, current_user.unit_system)["exercises"][-1],
        session_exercise_id=item.id,
    )


@views.route("/remove_session_exercise", methods=["POST"])
@login_required
def remove_session_exercise():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    remove_exercise(session, data.get("exercise_id"))
    return jsonify(success=True, message="Exercise removed from session.")


@views.route("/reorder_session_exercises", methods=["POST"])
@login_required
def reorder_session_exercises():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    reorder_exercises(session, data.get("exercise_ids"))
    return jsonify(success=True)


@views.route("/add_exercise_set", methods=["POST"])
@login_required
def add_exercise_set():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    record = save_set(
        session,
        data.get("exercise_id"),
        data.get("set_number"),
        data.get("reps"),
        data.get("weight"),
        data.get("rest_time"),
        current_user.unit_system,
    )
    return jsonify(success=True, set_id=record.id, message="Set saved.")


@views.route("/delete_exercise_set", methods=["POST"])
@login_required
def delete_exercise_set():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    delete_workout_set(session, data.get("exercise_id"), data.get("set_number"))
    return jsonify(success=True)


@views.route("/update_workout_session", methods=["POST"])
@login_required
def update_workout_session():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    update_workout(session, data.get("name"), data.get("notes"))
    return jsonify(success=True)


@views.route("/end_workout_session", methods=["POST"])
@login_required
def end_workout_session():
    data = json_payload()
    session = owned_session(current_user.id, data.get("session_id"), active_only=True)
    complete_workout(session, data.get("workout_name"), data.get("notes"))
    return jsonify(
        success=True,
        status="success",
        message="Workout saved.",
        redirect_url=url_for("views.dashboard"),
    )


@views.route("/discard_workout_session", methods=["POST"])
@login_required
def discard_workout_session():
    session = owned_session(current_user.id, json_payload().get("session_id"), active_only=True)
    db.session.delete(session)
    db.session.commit()
    return jsonify(success=True)


@views.route("/delete_session", methods=["POST"])
@login_required
def delete_session():
    session = owned_session(current_user.id, json_payload().get("sessionId"))
    db.session.delete(session)
    db.session.commit()
    return jsonify(success=True)


@views.route("/account")
@login_required
def account():
    return render_template(
        "account.html",
        user=current_user,
        password_form=ChangePasswordForm(),
        delete_form=DeleteAccountForm(),
    )


@views.route("/change-password", methods=["POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if not form.validate_on_submit():
        flash("Please correct the password form and try again.", "danger")
        return render_template(
            "account.html", user=current_user, password_form=form, delete_form=DeleteAccountForm()
        ), 400
    if not check_password_hash(current_user.password, form.current_password.data):
        form.current_password.errors.append("Current password is incorrect.")
        return render_template(
            "account.html", user=current_user, password_form=form, delete_form=DeleteAccountForm()
        ), 400
    if check_password_hash(current_user.password, form.new_password.data):
        form.new_password.errors.append("New password must be different from the current password.")
        return render_template(
            "account.html", user=current_user, password_form=form, delete_form=DeleteAccountForm()
        ), 400
    current_user.password = generate_password_hash(form.new_password.data)
    current_user.password_changed_at = datetime.now(timezone.utc)
    current_user.session_version += 1
    db.session.commit()
    logout_user()
    flash("Password changed. Please log in again on this and any other device.", "success")
    return redirect(url_for("auth.login"))


@views.route("/delete_account", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if not form.validate_on_submit() or not check_password_hash(current_user.password, form.current_password.data):
        if not form.current_password.errors:
            form.current_password.errors.append("Current password is incorrect.")
        flash("Account deletion was not confirmed.", "danger")
        return render_template(
            "account.html", user=current_user, password_form=ChangePasswordForm(), delete_form=form
        ), 400
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
        canonical_height = stored_height(height_form.height.data, current_user.unit_system)
        if not 50 <= canonical_height <= 300:
            height_form.height.errors.append("Enter a height equivalent to 50–300 cm.")
        else:
            record = db.session.scalar(
                db.select(Height).where(
                    Height.user_id == current_user.id, Height.date == height_form.date.data
                )
            )
            if record:
                record.height = round(canonical_height)
            else:
                db.session.add(
                    Height(user=current_user, height=round(canonical_height), date=height_form.date.data)
                )
            db.session.commit()
            return redirect(url_for("views.measurements"))
    if weight_form.submit.data and weight_form.validate_on_submit():
        canonical_weight = stored_weight(weight_form.weight.data, current_user.unit_system)
        if not 20 <= canonical_weight <= 500:
            weight_form.weight.errors.append("Enter a weight equivalent to 20–500 kg.")
        else:
            record = db.session.scalar(
                db.select(Weight).where(
                    Weight.user_id == current_user.id, Weight.date == weight_form.date.data
                )
            )
            if record:
                record.weight = canonical_weight
            else:
                db.session.add(
                    Weight(user=current_user, weight=canonical_weight, date=weight_form.date.data)
                )
            db.session.commit()
            return redirect(url_for("views.measurements"))

    height_rows = db.session.execute(
        db.select(Height.height, Height.date).where(Height.user_id == current_user.id).order_by(Height.date)
    ).all()
    weight_rows = db.session.execute(
        db.select(Weight.weight, Weight.date).where(Weight.user_id == current_user.id).order_by(Weight.date)
    ).all()
    heights = [display_height(value, current_user.unit_system) for value, _ in height_rows]
    height_dates = [date.strftime("%d %b %y") for _, date in height_rows]
    weights = [display_weight(value, current_user.unit_system) for value, _ in weight_rows]
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
        height_unit=height_unit(current_user.unit_system),
        weight_unit=weight_unit(current_user.unit_system),
    )
