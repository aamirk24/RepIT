"""Add production exercise catalogue metadata

Revision ID: f1d52f894ef8
Revises: f6c07333502d
Create Date: 2026-08-16 01:35:16.126304

"""
from alembic import op
import sqlalchemy as sa
import re


# revision identifiers, used by Alembic.
revision = 'f1d52f894ef8'
down_revision = 'f6c07333502d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('exercise', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('body_part', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('equipment', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('difficulty', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('category', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('source_identifier', sa.String(length=180), nullable=True))
        batch_op.add_column(sa.Column('source_url', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('license_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('license_url', sa.String(length=1000), nullable=True))
        batch_op.add_column(sa.Column('attribution_text', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('catalog_version', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    exercise = sa.table(
        'exercise',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('slug', sa.String),
        sa.column('description', sa.Text),
        sa.column('body_part', sa.String),
        sa.column('equipment', sa.String),
        sa.column('difficulty', sa.String),
        sa.column('category', sa.String),
        sa.column('source_identifier', sa.String),
        sa.column('catalog_version', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )
    connection = op.get_bind()
    for row in connection.execute(sa.select(exercise.c.id, exercise.c.name)):
        slug = re.sub(r'[^a-z0-9]+', '-', row.name.lower()).strip('-')
        connection.execute(
            exercise.update().where(exercise.c.id == row.id).values(
                slug=slug,
                description=f'{row.name} exercise guidance.',
                body_part='full body',
                equipment='other',
                difficulty='beginner',
                category='strength',
                source_identifier=slug,
                catalog_version='stage-0-migrated',
                is_active=True,
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )

    with op.batch_alter_table('exercise', schema=None) as batch_op:
        batch_op.alter_column('slug', nullable=False)
        batch_op.alter_column('description', nullable=False)
        batch_op.alter_column('body_part', nullable=False)
        batch_op.alter_column('equipment', nullable=False)
        batch_op.alter_column('difficulty', nullable=False)
        batch_op.alter_column('category', nullable=False)
        batch_op.alter_column('source_identifier', nullable=False)
        batch_op.alter_column('catalog_version', nullable=False)
        batch_op.alter_column('is_active', nullable=False)
        batch_op.alter_column('created_at', nullable=False)
        batch_op.alter_column('updated_at', nullable=False)
        batch_op.create_index(batch_op.f('ix_exercise_body_part'), ['body_part'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercise_category'), ['category'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercise_difficulty'), ['difficulty'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercise_equipment'), ['equipment'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercise_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_exercise_slug'), ['slug'], unique=True)
        batch_op.create_check_constraint('ck_exercise_difficulty', "difficulty IN ('beginner', 'intermediate', 'advanced')")
        batch_op.create_check_constraint('ck_exercise_category', "category IN ('strength', 'cardio', 'mobility', 'balance', 'stretching', 'plyometrics', 'rehabilitation', 'stability')")
        batch_op.create_unique_constraint('uq_exercise_source_identifier', ['source', 'source_identifier'])



def downgrade():
    with op.batch_alter_table('exercise', schema=None) as batch_op:
        batch_op.drop_constraint('uq_exercise_source_identifier', type_='unique')
        batch_op.drop_constraint('ck_exercise_category', type_='check')
        batch_op.drop_constraint('ck_exercise_difficulty', type_='check')
        batch_op.drop_index(batch_op.f('ix_exercise_slug'))
        batch_op.drop_index(batch_op.f('ix_exercise_is_active'))
        batch_op.drop_index(batch_op.f('ix_exercise_equipment'))
        batch_op.drop_index(batch_op.f('ix_exercise_difficulty'))
        batch_op.drop_index(batch_op.f('ix_exercise_category'))
        batch_op.drop_index(batch_op.f('ix_exercise_body_part'))
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('catalog_version')
        batch_op.drop_column('attribution_text')
        batch_op.drop_column('license_url')
        batch_op.drop_column('license_name')
        batch_op.drop_column('source_url')
        batch_op.drop_column('source_identifier')
        batch_op.drop_column('category')
        batch_op.drop_column('difficulty')
        batch_op.drop_column('equipment')
        batch_op.drop_column('body_part')
        batch_op.drop_column('description')
        batch_op.drop_column('slug')
