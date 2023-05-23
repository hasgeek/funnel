"""Add Rsvp.uuid.

Revision ID: 7f8114c73092
Revises: 931be3605dc4
Create Date: 2020-08-18 22:45:58.557775

"""

from typing import Optional, Tuple, Union
from uuid import uuid4

from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table
import progressbar.widgets
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7f8114c73092'
down_revision = '931be3605dc4'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


rsvp = table(
    'rsvp',
    column('project_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('uuid', sa.Uuid()),
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
    op.add_column('rsvp', sa.Column('uuid', sa.Uuid(), nullable=True))

    count = conn.scalar(sa.select(sa.func.count('*')).select_from(rsvp))
    progress = get_progressbar("Rsvps", count)
    progress.start()

    items = conn.execute(sa.select(rsvp.c.project_id, rsvp.c.user_id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(rsvp)
            .where(
                sa.and_(
                    rsvp.c.project_id == item.project_id, rsvp.c.user_id == item.user_id
                )
            )
            .values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('rsvp', 'uuid', nullable=False)
    op.create_unique_constraint('rsvp_uuid_key', 'rsvp', ['uuid'])


def downgrade():
    op.drop_constraint('rsvp_uuid_key', 'rsvp', type_='unique')
    op.drop_column('rsvp', 'uuid')
