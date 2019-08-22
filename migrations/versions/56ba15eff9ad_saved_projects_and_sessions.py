# -*- coding: utf-8 -*-

"""Saved projects and sessions

Revision ID: 56ba15eff9ad
Revises: 5e06feda611d
Create Date: 2019-07-04 14:32:53.383544

"""

# revision identifiers, used by Alembic.
revision = '56ba15eff9ad'
down_revision = '5e06feda611d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'saved_project',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('saved_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['project.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'project_id'),
    )
    op.create_index(
        op.f('ix_saved_project_project_id'),
        'saved_project',
        ['project_id'],
        unique=False,
    )

    op.create_table(
        'saved_session',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('saved_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('description', sa.UnicodeText(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['session.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'session_id'),
    )
    op.create_index(
        op.f('ix_saved_session_session_id'),
        'saved_session',
        ['session_id'],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f('ix_saved_session_session_id'), table_name='saved_session')
    op.drop_table('saved_session')

    op.drop_index(op.f('ix_saved_project_project_id'), table_name='saved_project')
    op.drop_table('saved_project')
