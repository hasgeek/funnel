"""add_title_to_event

Revision ID: 39eed1e99156
Revises: 4083b7bd0cc8
Create Date: 2015-07-07 19:34:04.129355

"""

revision = '39eed1e99156'
down_revision = '4083b7bd0cc8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('event', sa.Column('title', sa.Unicode(length=250), nullable=True))
    op.create_unique_constraint("event_proposal_space_id_name", 'event', ['proposal_space_id', 'name'])


def downgrade():
    op.drop_constraint("event_proposal_space_id_name", 'event', type_='unique')
    op.drop_column('event', 'title')
