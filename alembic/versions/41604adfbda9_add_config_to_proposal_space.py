"""add config to proposal space

Revision ID: 41604adfbda9
Revises: 2c64e60b80a
Create Date: 2015-05-04 19:24:01.480136

"""

revision = '41604adfbda9'
down_revision = '2c64e60b80a'

from alembic import op
import sqlalchemy as sa
from coaster.sqlalchemy import JsonDict


def upgrade():
    op.add_column('proposal_space', sa.Column('config', JsonDict(), server_default='{}', nullable=False))


def downgrade():
    op.drop_column('proposal_space', 'config')
