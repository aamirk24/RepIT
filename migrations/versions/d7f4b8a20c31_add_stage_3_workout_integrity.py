"""Add Stage 3 workout lifecycle integrity

Revision ID: d7f4b8a20c31
Revises: c3a891b6e204
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "d7f4b8a20c31"
down_revision = "c3a891b6e204"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_session") as batch_op:
        batch_op.add_column(sa.Column("name", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.alter_column("notes", existing_type=sa.String(length=200), type_=sa.Text(), nullable=True)

    op.execute(
        sa.text(
            "UPDATE workout_session "
            "SET name = COALESCE(NULLIF(notes, ''), 'Custom Workout'), notes = NULL, "
            "updated_at = COALESCE(end_time, start_time)"
        )
    )
    with op.batch_alter_table("workout_session") as batch_op:
        batch_op.alter_column("name", existing_type=sa.String(length=150), nullable=False)
        batch_op.alter_column("updated_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.create_check_constraint("ck_workout_session_time_order", "end_time IS NULL OR end_time >= start_time")
        batch_op.create_check_constraint("ck_workout_session_name_length", "length(trim(name)) BETWEEN 1 AND 150")
        batch_op.create_check_constraint("ck_workout_session_notes_length", "notes IS NULL OR length(notes) <= 2000")

    connection = op.get_bind()
    active_rows = connection.execute(
        sa.text("SELECT id, user_id, start_time FROM workout_session WHERE end_time IS NULL ORDER BY user_id, start_time DESC, id DESC")
    ).mappings()
    seen_users = set()
    for row in active_rows:
        if row["user_id"] in seen_users:
            connection.execute(
                sa.text("UPDATE workout_session SET end_time = start_time WHERE id = :id"), {"id": row["id"]}
            )
        else:
            seen_users.add(row["user_id"])

    op.create_index(
        "uq_workout_session_active_user",
        "workout_session",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("end_time IS NULL"),
        postgresql_where=sa.text("end_time IS NULL"),
    )

    with op.batch_alter_table("session_exercise") as batch_op:
        batch_op.add_column(sa.Column("exercise_name", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("target_name", sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column("equipment_name", sa.String(length=100), nullable=True))

    op.execute(
        sa.text(
            "UPDATE session_exercise SET "
            "exercise_name = (SELECT name FROM exercise WHERE exercise.id = session_exercise.exercise_id), "
            "target_name = (SELECT target FROM exercise WHERE exercise.id = session_exercise.exercise_id), "
            "equipment_name = (SELECT equipment FROM exercise WHERE exercise.id = session_exercise.exercise_id)"
        )
    )

    rows = connection.execute(
        sa.text("SELECT id, workout_session_id FROM session_exercise ORDER BY workout_session_id, \"order\", id")
    ).mappings()
    positions = {}
    for row in rows:
        positions[row["workout_session_id"]] = positions.get(row["workout_session_id"], 0) + 1
        connection.execute(
            sa.text('UPDATE session_exercise SET "order" = :position WHERE id = :id'),
            {"position": positions[row["workout_session_id"]], "id": row["id"]},
        )

    with op.batch_alter_table("session_exercise") as batch_op:
        batch_op.alter_column("exercise_name", existing_type=sa.String(length=150), nullable=False)
        batch_op.alter_column("target_name", existing_type=sa.String(length=150), nullable=False)
        batch_op.alter_column("equipment_name", existing_type=sa.String(length=100), nullable=False)
        batch_op.create_unique_constraint(
            "uq_session_exercise_exercise", ["workout_session_id", "exercise_id"]
        )
        batch_op.create_unique_constraint("uq_session_exercise_order", ["workout_session_id", "order"])
        batch_op.create_check_constraint("ck_session_exercise_order_positive", '"order" >= 1')

    with op.batch_alter_table("exercise_set") as batch_op:
        batch_op.create_unique_constraint("uq_exercise_set_number", ["session_exercise_id", "set_number"])
        batch_op.create_check_constraint("ck_exercise_set_number_positive", "set_number >= 1")
        batch_op.create_check_constraint("ck_exercise_set_reps_positive", "reps >= 1")
        batch_op.create_check_constraint("ck_exercise_set_weight_nonnegative", "weight IS NULL OR weight >= 0")
        batch_op.create_check_constraint("ck_exercise_set_rest_nonnegative", "rest_time IS NULL OR rest_time >= 0")


def downgrade():
    with op.batch_alter_table("exercise_set") as batch_op:
        batch_op.drop_constraint("ck_exercise_set_rest_nonnegative", type_="check")
        batch_op.drop_constraint("ck_exercise_set_weight_nonnegative", type_="check")
        batch_op.drop_constraint("ck_exercise_set_reps_positive", type_="check")
        batch_op.drop_constraint("ck_exercise_set_number_positive", type_="check")
        batch_op.drop_constraint("uq_exercise_set_number", type_="unique")

    with op.batch_alter_table("session_exercise") as batch_op:
        batch_op.drop_constraint("ck_session_exercise_order_positive", type_="check")
        batch_op.drop_constraint("uq_session_exercise_order", type_="unique")
        batch_op.drop_constraint("uq_session_exercise_exercise", type_="unique")
        batch_op.drop_column("equipment_name")
        batch_op.drop_column("target_name")
        batch_op.drop_column("exercise_name")

    op.drop_index("uq_workout_session_active_user", table_name="workout_session")
    op.execute(sa.text("UPDATE workout_session SET notes = substr(COALESCE(notes, name), 1, 200)"))
    with op.batch_alter_table("workout_session") as batch_op:
        batch_op.drop_constraint("ck_workout_session_notes_length", type_="check")
        batch_op.drop_constraint("ck_workout_session_name_length", type_="check")
        batch_op.drop_constraint("ck_workout_session_time_order", type_="check")
        batch_op.alter_column("notes", existing_type=sa.Text(), type_=sa.String(length=200), nullable=False)
        batch_op.drop_column("updated_at")
        batch_op.drop_column("name")
