"""Add session featured field.

Revision ID: d6b1904bea0e
Revises: 70ffbc1bcf88
Create Date: 2018-11-20 17:22:11.582473

"""

revision = 'd6b1904bea0e'
down_revision = '70ffbc1bcf88'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_column('session', 'featured')
