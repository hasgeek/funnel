# -*- coding: utf-8 -*-

"""add session featured field

Revision ID: d6b1904bea0e
Revises: 70ffbc1bcf88
Create Date: 2018-11-20 17:22:11.582473

"""

revision = 'd6b1904bea0e'
down_revision = '70ffbc1bcf88'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column(
        'session',
        sa.Column(
            'featured',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('session', 'featured', server_default=None)


def downgrade():
    op.drop_column('session', 'featured')
