# -*- coding: utf-8 -*-

"""Team model

Revision ID: 140c9b68d65b
Revises: 1bb2df0df8e2
Create Date: 2014-04-07 03:22:09.472270

"""

# revision identifiers, used by Alembic.
revision = '140c9b68d65b'
down_revision = '1bb2df0df8e2'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.create_table(
        'team',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('title', sa.Unicode(length=250), nullable=False),
        sa.Column('userid', sa.String(length=22), nullable=False),
        sa.Column('owners', sa.Boolean(), nullable=False),
        sa.Column('orgid', sa.String(length=22), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('userid'),
    )
    op.create_table(
        'users_teams',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['team.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('user_id', 'team_id'),
    )
    op.drop_column('user', 'description')


def downgrade():
    op.add_column(
        'user',
        sa.Column(
            'description', sa.TEXT(), nullable=False, server_default=sa.text(u"''")
        ),
    )
    op.alter_column('user', 'description', server_default=None)

    op.drop_table('users_teams')
    op.drop_table('team')
