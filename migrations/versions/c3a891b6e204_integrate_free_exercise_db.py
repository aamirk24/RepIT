"""Integrate Free Exercise DB catalogue fields

Revision ID: c3a891b6e204
Revises: 9e1c7a4b2d10
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "c3a891b6e204"
down_revision = "9e1c7a4b2d10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("exercise") as batch_op:
        batch_op.drop_constraint("ck_exercise_difficulty", type_="check")
        batch_op.drop_constraint("ck_exercise_category", type_="check")
        batch_op.add_column(sa.Column("image_urls", sa.JSON(), nullable=True))
        batch_op.create_check_constraint(
            "ck_exercise_difficulty",
            "difficulty IN ('beginner', 'intermediate', 'advanced', 'expert')",
        )
        batch_op.create_check_constraint(
            "ck_exercise_category",
            "category IN ('strength', 'cardio', 'mobility', 'balance', 'stretching', 'plyometrics', 'rehabilitation', 'stability', 'powerlifting', 'olympic weightlifting', 'strongman')",
        )

    op.execute(sa.text("UPDATE exercise SET image_urls = '[]' WHERE image_urls IS NULL"))
    with op.batch_alter_table("exercise") as batch_op:
        batch_op.alter_column("image_urls", existing_type=sa.JSON(), nullable=False)


def downgrade():
    # Preserve routine/history foreign keys while mapping values back to Stage 1's narrower vocabulary.
    op.execute(sa.text("UPDATE exercise SET difficulty = 'advanced' WHERE difficulty = 'expert'"))
    op.execute(
        sa.text(
            "UPDATE exercise SET category = 'strength' "
            "WHERE category IN ('powerlifting', 'olympic weightlifting', 'strongman')"
        )
    )
    with op.batch_alter_table("exercise") as batch_op:
        batch_op.drop_constraint("ck_exercise_difficulty", type_="check")
        batch_op.drop_constraint("ck_exercise_category", type_="check")
        batch_op.drop_column("image_urls")
        batch_op.create_check_constraint(
            "ck_exercise_difficulty",
            "difficulty IN ('beginner', 'intermediate', 'advanced')",
        )
        batch_op.create_check_constraint(
            "ck_exercise_category",
            "category IN ('strength', 'cardio', 'mobility', 'balance', 'stretching', 'plyometrics', 'rehabilitation', 'stability')",
        )
