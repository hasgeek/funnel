"""Comment uuid field.

Revision ID: c3069d33419a
Revises: 69c2ced88981
Create Date: 2018-12-11 19:33:42.261815

"""

revision = 'c3069d33419a'
down_revision = '69c2ced88981'

from uuid import uuid4

from alembic import op
from progressbar import ProgressBar
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import progressbar.widgets
import sqlalchemy as sa

comment = table(
    'comment', column('id', sa.Integer()), column('uuid', postgresql.UUID())
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

    op.add_column('comment', sa.Column('uuid', postgresql.UUID(), nullable=True))

    count = conn.scalar(sa.select(sa.func.count('*')).select_from(comment))
    progress = get_progressbar("Comments", count)
    progress.start()
    items = conn.execute(sa.select(comment.c.id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(comment).where(comment.c.id == item.id).values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('comment', 'uuid', nullable=False)

    op.create_unique_constraint('comment_uuid_key', 'comment', ['uuid'])


def downgrade():
    op.drop_constraint('comment_uuid_key', 'comment', type_='unique')
    op.drop_column('comment', 'uuid')
