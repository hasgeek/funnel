"""Trello id data

Revision ID: 489173017298
Revises: 570f4ea99cda
Create Date: 2016-02-10 15:57:47.766333

"""
from alembic import op
import sqlalchemy as sa
import coaster
# revision identifiers, used by Alembic.
revision = '489173017298'
down_revision = '570f4ea99cda'


def upgrade():
    op.add_column('proposal', sa.Column('external_config', coaster.sqlalchemy.JsonDict(), server_default='{}', nullable=False))
    op.add_column('proposal_space', sa.Column('external_config', coaster.sqlalchemy.JsonDict(), server_default='{}', nullable=False))


def downgrade():
    op.drop_column('proposal_space', 'external_config')
    op.drop_column('proposal', 'external_config')
