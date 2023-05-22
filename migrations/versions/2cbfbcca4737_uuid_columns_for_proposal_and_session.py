"""UUID columns for Proposal and Session.

Revision ID: 2cbfbcca4737
Revises: cd8d073d7557
Create Date: 2018-11-09 08:53:46.321710

"""

# revision identifiers, used by Alembic.
revision = '2cbfbcca4737'
down_revision = 'cd8d073d7557'

from uuid import uuid4

from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table
import progressbar.widgets
import sqlalchemy as sa

proposal = table('proposal', column('id', sa.Integer()), column('uuid', sa.Uuid()))

session = table('session', column('id', sa.Integer()), column('uuid', sa.Uuid()))


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

    op.add_column('proposal', sa.Column('uuid', sa.Uuid(), nullable=True))
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(proposal))
    progress = get_progressbar("Proposals", count)
    progress.start()
    items = conn.execute(sa.select(proposal.c.id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(proposal).where(proposal.c.id == item.id).values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('proposal', 'uuid', nullable=False)
    op.create_unique_constraint('proposal_uuid_key', 'proposal', ['uuid'])

    op.add_column('session', sa.Column('uuid', sa.Uuid(), nullable=True))
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(session))
    progress = get_progressbar("Sessions", count)
    progress.start()
    items = conn.execute(sa.select(session.c.id))
    for counter, item in enumerate(items):
        conn.execute(
            sa.update(session).where(session.c.id == item.id).values(uuid=uuid4())
        )
        progress.update(counter)
    progress.finish()
    op.alter_column('session', 'uuid', nullable=False)
    op.create_unique_constraint('session_uuid_key', 'session', ['uuid'])


def downgrade():
    op.drop_constraint('session_uuid_key', 'session', type_='unique')
    op.drop_column('session', 'uuid')
    op.drop_constraint('proposal_uuid_key', 'proposal', type_='unique')
    op.drop_column('proposal', 'uuid')
