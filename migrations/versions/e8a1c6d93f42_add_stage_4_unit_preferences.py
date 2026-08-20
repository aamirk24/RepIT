"""Add Stage 4 unit preferences

Revision ID: e8a1c6d93f42
Revises: d7f4b8a20c31
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "e8a1c6d93f42"
down_revision = "d7f4b8a20c31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("unit_system", sa.String(length=10), nullable=False, server_default="metric")
        )
        batch_op.create_check_constraint("ck_user_unit_system", "unit_system IN ('metric', 'imperial')")
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("unit_system", server_default=None)
    op.create_index("ix_workout_session_user_start", "workout_session", ["user_id", "start_time"])
    op.create_index("ix_session_exercise_exercise_id", "session_exercise", ["exercise_id"])


def downgrade():
    op.drop_index("ix_session_exercise_exercise_id", table_name="session_exercise")
    op.drop_index("ix_workout_session_user_start", table_name="workout_session")
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_constraint("ck_user_unit_system", type_="check")
        batch_op.drop_column("unit_system")
