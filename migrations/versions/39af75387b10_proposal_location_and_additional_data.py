"""Proposal location and additional data

Revision ID: 39af75387b10
Revises: 50f58275fc1c
Create Date: 2015-01-15 21:41:58.144843

"""

# revision identifiers, used by Alembic.
revision = '39af75387b10'
down_revision = '50f58275fc1c'

from alembic import op
import sqlalchemy as sa
from coaster.sqlalchemy import JsonDict


def upgrade():
    op.add_column('proposal', sa.Column('data', JsonDict(), server_default='{}', nullable=False))
    op.add_column('proposal', sa.Column('latitude', sa.Numeric(), nullable=True))
    op.add_column('proposal', sa.Column('longitude', sa.Numeric(), nullable=True))


def downgrade():
    op.drop_column('proposal', 'longitude')
    op.drop_column('proposal', 'latitude')
    op.drop_column('proposal', 'data')
