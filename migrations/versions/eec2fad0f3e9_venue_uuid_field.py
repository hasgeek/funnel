"""Venue uuid field.

Revision ID: eec2fad0f3e9
Revises: ae68621248af
Create Date: 2018-11-29 15:30:20.041207

"""

revision = 'eec2fad0f3e9'
down_revision = 'ae68621248af'

from uuid import uuid4

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

venue = table('venue', column('id', sa.Integer()), column('uuid', postgresql.UUID()))


def get_progressbar(label, maxval):
    return ProgressBar(
        maxval=maxval,
        widgets=[
            label,
            ': ',
            progressbar.widgets.Percentage(),
            ' ',
            progressbar.widgets.Bar(),
            ' ',
            progressbar.widgets.ETA(),
            ' ',
        ],
    )


def upgrade():
    conn = op.get_bind()

    op.add_column('venue', sa.Column('uuid', postgresql.UUID(), nullable=True))
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(venue))
    progress = get_progressbar("Venues", count)
    progress.start()
    items = conn.execute(sa.select(venue.c.id))
    for counter, item in enumerate(items):
        conn.execute(sa.update(venue).where(venue.c.id == item.id).values(uuid=uuid4()))
        progress.update(counter)
    progress.finish()
    op.alter_column('venue', 'uuid', nullable=False)
    op.create_unique_constraint('venue_uuid_key', 'venue', ['uuid'])


def downgrade():
    op.drop_constraint('venue_uuid_key', 'venue', type_='unique')
    op.drop_column('venue', 'uuid')
