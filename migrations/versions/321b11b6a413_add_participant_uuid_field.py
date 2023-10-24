"""Add participant uuid field.

Revision ID: 321b11b6a413
Revises: 664141d5ec56
Create Date: 2020-01-30 09:35:52.565945

"""

# revision identifiers, used by Alembic.
revision = '321b11b6a413'
down_revision = '664141d5ec56'

from uuid import uuid4

import progressbar.widgets
import sqlalchemy as sa
from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table

participant = table(
    'participant', column('id', sa.Integer()), column('uuid', sa.Uuid())
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


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column('participant', sa.Column('uuid', sa.Uuid(), nullable=True))
    # migrate past participants
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(participant))
    progress = get_progressbar("Participants", count)
    progress.start()
    items = conn.execute(sa.select(participant.c.id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(participant)
            .where(participant.c.id == item.id)
            .values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('participant', 'uuid', nullable=False)
    op.create_unique_constraint('participant_uuid_key', 'participant', ['uuid'])


def downgrade() -> None:
    op.drop_constraint('participant_uuid_key', 'participant', type_='unique')
    op.drop_column('participant', 'uuid')
