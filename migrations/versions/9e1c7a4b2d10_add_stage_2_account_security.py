"""Add Stage 2 account security state

Revision ID: 9e1c7a4b2d10
Revises: f1d52f894ef8
Create Date: 2026-08-16
"""

from alembic import op
import sqlalchemy as sa


revision = "9e1c7a4b2d10"
down_revision = "f1d52f894ef8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))

    op.execute(sa.text("UPDATE user SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column("created_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column("session_version", server_default=None)

    op.create_table(
        "login_throttle",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("key_hash"),
    )


def downgrade():
    op.drop_table("login_throttle")
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("session_version")
        batch_op.drop_column("password_changed_at")
        batch_op.drop_column("created_at")
