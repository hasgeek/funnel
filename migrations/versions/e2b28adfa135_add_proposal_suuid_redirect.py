"""Add proposal_suuid_redirect.

Revision ID: e2b28adfa135
Revises: 41a4531be082
Create Date: 2020-04-20 03:31:29.101725

"""

from typing import Optional, Tuple, Union

import progressbar.widgets
import sqlalchemy as sa
from alembic import op
from progressbar import ProgressBar
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = 'e2b28adfa135'
down_revision = '41a4531be082'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('uuid', sa.Uuid(as_uuid=True)),
)

proposal_suuid_redirect = table(
    'proposal_suuid_redirect',
    column('id', sa.Integer()),
    column('proposal_id', sa.Integer()),
    column('suuid', sa.Unicode(22)),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
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
    # Import inside the `upgrade` function because `uuid2suuid` will be removed from
    # Coaster shortly. Importing this migration should not break in the future unless
    # also attempting to perform the migration, which will hopefully be unnecessary
    from coaster.utils import uuid2suuid

    op.create_table(
        'proposal_suuid_redirect',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=False),
        sa.Column('suuid', sa.Unicode(length=22), nullable=False),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_proposal_suuid_redirect_suuid'),
        'proposal_suuid_redirect',
        ['suuid'],
        unique=False,
    )

    conn = op.get_bind()
    count = conn.scalar(sa.select(sa.func.count('*')).select_from(proposal))
    progress = get_progressbar("Proposals", count)
    progress.start()
    items = conn.execute(sa.select(proposal.c.id, proposal.c.uuid))
    for counter, item in enumerate(items):
        conn.execute(
            proposal_suuid_redirect.insert().values(
                {
                    'created_at': sa.func.utcnow(),
                    'updated_at': sa.func.utcnow(),
                    'proposal_id': item.id,
                    'suuid': uuid2suuid(item.uuid),
                }
            )
        )
        progress.update(counter)
    progress.finish()


def downgrade() -> None:
    op.drop_index(
        op.f('ix_proposal_suuid_redirect_suuid'), table_name='proposal_suuid_redirect'
    )
    op.drop_table('proposal_suuid_redirect')
