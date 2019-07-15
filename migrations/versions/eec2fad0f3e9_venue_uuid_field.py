# -*- coding: utf-8 -*-

"""venue uuid field

Revision ID: eec2fad0f3e9
Revises: ae68621248af
Create Date: 2018-11-29 15:30:20.041207

"""

revision = 'eec2fad0f3e9'
down_revision = 'ae68621248af'

from uuid import uuid4

import sqlalchemy as sa  # NOQA
from alembic import op
from sqlalchemy.sql import column, table
from sqlalchemy_utils import UUIDType

import progressbar.widgets
from progressbar import ProgressBar

venue = table(
    'venue', column('id', sa.Integer()), column('uuid', UUIDType(binary=False))
)


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

    op.add_column('venue', sa.Column('uuid', UUIDType(binary=False), nullable=True))
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(venue))
    progress = get_progressbar("Venues", count)
    progress.start()
    items = conn.execute(sa.select([venue.c.id]))
    for counter, item in enumerate(items):
        conn.execute(sa.update(venue).where(venue.c.id == item.id).values(uuid=uuid4()))
        progress.update(counter)
    progress.finish()
    op.alter_column('venue', 'uuid', nullable=False)
    op.create_unique_constraint('venue_uuid_key', 'venue', ['uuid'])


def downgrade():
    op.drop_constraint('venue_uuid_key', 'venue', type_='unique')
    op.drop_column('venue', 'uuid')
