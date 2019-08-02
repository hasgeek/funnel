# -*- coding: utf-8 -*-

"""space date upto

Revision ID: 31253f116e1e
Revises: 4aedc1062818
Create Date: 2013-11-14 22:15:44.749221

"""

# revision identifiers, used by Alembic.
revision = '31253f116e1e'
down_revision = '4aedc1062818'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column('proposal_space', sa.Column('date_upto', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('proposal_space', 'date_upto')
