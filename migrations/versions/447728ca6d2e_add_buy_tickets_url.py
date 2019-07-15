# -*- coding: utf-8 -*-

"""empty message

Revision ID: 447728ca6d2e
Revises: 14d1424b47
Create Date: 2015-04-06 16:43:50.255747

"""

# revision identifiers, used by Alembic.
revision = '447728ca6d2e'
down_revision = '14d1424b47'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.add_column(
        'proposal_space',
        sa.Column('buy_tickets_url', sa.Unicode(length=250), nullable=True),
    )


def downgrade():
    op.drop_column('proposal_space', 'buy_tickets_url')
