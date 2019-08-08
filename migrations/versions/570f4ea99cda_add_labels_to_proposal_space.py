# -*- coding: utf-8 -*-

"""add labels to proposal space

Revision ID: 570f4ea99cda
Revises: 3b189f2e5c56
Create Date: 2016-02-02 20:45:07.804542

"""

# revision identifiers, used by Alembic.
revision = '570f4ea99cda'
down_revision = '3b189f2e5c56'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa  # NOQA

from coaster.sqlalchemy import JsonDict


def upgrade():
    proposal_space = table('proposal_space', column('labels'))
    op.add_column(
        u'proposal_space',
        sa.Column('labels', JsonDict(), server_default='{}', nullable=False),
    )
    op.execute(
        proposal_space.update().values(
            {
                'labels': '{"proposal": {"part_a": {"title": "Objective", "hint": "What is the expected benefit for someone attending this?"}, "part_b": {"title": "Description", "hint": "A detailed description of the session."}}}'
            }
        )
    )


def downgrade():
    op.drop_column(u'proposal_space', 'labels')
