# -*- coding: utf-8 -*-

"""Remove unused proposal.data

Revision ID: 752dee4ae101
Revises: 3afa589814a9
Create Date: 2019-06-06 15:23:00.280127

"""

# revision identifiers, used by Alembic.
revision = '752dee4ae101'
down_revision = '3afa589814a9'

from alembic import op
import sqlalchemy as sa  # NOQA

from coaster.sqlalchemy import JsonDict


def upgrade():
    op.drop_column('proposal', 'data')


def downgrade():
    op.add_column(
        'proposal',
        sa.Column(
            'data',
            JsonDict(),
            server_default=sa.text("'{}'"),
            autoincrement=False,
            nullable=False,
        ),
    )
