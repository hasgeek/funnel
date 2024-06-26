"""Adding uuid to commentset.

Revision ID: 887db555cca9
Revises: 222b78a8508d
Create Date: 2020-05-08 19:16:15.324555

"""

from uuid import uuid4

import progressbar.widgets
import sqlalchemy as sa
from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = '887db555cca9'
down_revision = '222b78a8508d'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


commentset = table('commentset', column('id', sa.Integer()), column('uuid', sa.Uuid()))


def get_progressbar(label: str, maxval: int | None) -> ProgressBar:
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

    op.add_column('commentset', sa.Column('uuid', sa.Uuid(), nullable=True))

    count = conn.scalar(sa.select(sa.func.count(sa.text('*'))).select_from(commentset))
    progress = get_progressbar("Commentsets", count)
    progress.start()
    items = conn.execute(sa.select(commentset.c.id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(commentset).where(commentset.c.id == item.id).values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()

    op.alter_column('commentset', 'uuid', nullable=False)
    op.create_unique_constraint('commentset_uuid_key', 'commentset', ['uuid'])


def downgrade() -> None:
    op.drop_constraint('commentset_uuid_key', 'commentset', type_='unique')
    op.drop_column('commentset', 'uuid')
