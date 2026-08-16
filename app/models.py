from datetime import datetime, timezone

from flask_login import UserMixin

from . import db


workout_exercise = db.Table(
    "workout_exercise",
    db.Column("workout_id", db.Integer, db.ForeignKey("workout.id", ondelete="CASCADE"), primary_key=True),
    db.Column("exercise_id", db.Integer, db.ForeignKey("exercise.id"), primary_key=True),
)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    birthdate = db.Column(db.Date)
    gender = db.Column(db.String(20))
    city = db.Column(db.String(150))
    county = db.Column(db.String(150))
    country = db.Column(db.String(150))

    workouts = db.relationship("Workout", back_populates="creator", cascade="all, delete-orphan")
    workout_sessions = db.relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")
    heights = db.relationship("Height", back_populates="user", cascade="all, delete-orphan")
    weights = db.relationship("Weight", back_populates="user", cascade="all, delete-orphan")


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    target = db.Column(db.String(150), nullable=False)
    secondary_muscles = db.Column(db.JSON, nullable=False, default=list)
    instructions = db.Column(db.JSON, nullable=False, default=list)
    image_url = db.Column(db.String(1000))
    source = db.Column(db.String(100), nullable=False, default="RepIT")

    workouts = db.relationship("Workout", secondary=workout_exercise, back_populates="exercises")
    session_exercises = db.relationship("SessionExercise", back_populates="exercise")

    # Compatibility aliases for the original templates.
    @property
    def secondaryMuscles(self):
        return self.secondary_muscles

    @property
    def gifUrl(self):
        return self.image_url


class Workout(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(1000))
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)

    creator = db.relationship("User", back_populates="workouts")
    exercises = db.relationship("Exercise", secondary=workout_exercise, back_populates="workouts")
    workout_sessions = db.relationship("WorkoutSession", back_populates="workout")


class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    workout_id = db.Column(db.Integer, db.ForeignKey("workout.id", ondelete="SET NULL"))
    start_time = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True))
    notes = db.Column(db.String(200), nullable=False, default="Custom Workout")

    user = db.relationship("User", back_populates="workout_sessions")
    workout = db.relationship("Workout", back_populates="workout_sessions")
    session_exercises = db.relationship(
        "SessionExercise", back_populates="workout_session", cascade="all, delete-orphan", order_by="SessionExercise.order"
    )


class SessionExercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_session_id = db.Column(
        db.Integer, db.ForeignKey("workout_session.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercise.id"), nullable=False)
    order = db.Column(db.Integer, nullable=False)

    workout_session = db.relationship("WorkoutSession", back_populates="session_exercises")
    exercise = db.relationship("Exercise", back_populates="session_exercises")
    sets = db.relationship(
        "ExerciseSet", back_populates="session_exercise", cascade="all, delete-orphan", order_by="ExerciseSet.set_number"
    )


class ExerciseSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_exercise_id = db.Column(
        db.Integer, db.ForeignKey("session_exercise.id", ondelete="CASCADE"), nullable=False, index=True
    )
    set_number = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float)
    rest_time = db.Column(db.Integer)
    is_completed = db.Column(db.Boolean, nullable=False, default=True)

    session_exercise = db.relationship("SessionExercise", back_populates="sets")


class Height(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_height_user_date"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    height = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    user = db.relationship("User", back_populates="heights")


class Weight(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_weight_user_date"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    weight = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    user = db.relationship("User", back_populates="weights")
