"""Populate ProposalMembership.

Revision ID: fa05ebecbc0f
Revises: 82303877b746
Create Date: 2021-04-30 04:07:47.387372

"""

from uuid import uuid4

from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import column, table
import sqlalchemy as sa

from progressbar import ProgressBar
import progressbar.widgets

# revision identifiers, used by Alembic.
revision = 'fa05ebecbc0f'
down_revision = '82303877b746'
branch_labels = None
depends_on = None

#: Label for proposers who were asking for someone else to speak (legacy use, English)
PROPOSING_LABEL = "Proposing"


class MEMBERSHIP_RECORD_TYPE:
    INVITE = 0
    ACCEPT = 1
    DIRECT_ADD = 2
    AMEND = 3


proposal = table(
    'proposal',
    column('id', sa.Integer()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('user_id', sa.Integer()),
    column('speaker_id', sa.Integer()),
)

proposal_membership = table(
    'proposal_membership',
    column('id', postgresql.UUID()),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('granted_at', sa.TIMESTAMP(timezone=True)),
    column('granted_by_id', sa.Integer()),
    column('record_type', sa.Integer()),
    column('proposal_id', sa.Integer()),
    column('user_id', sa.Integer()),
    column('is_uncredited', sa.Boolean()),
    column('seq', sa.Integer()),
    column('label', sa.String()),
)


def membership_values(proposal_row):
    return {
        'id': uuid4().hex,
        'created_at': sa.func.now(),
        'updated_at': sa.func.now(),
        'record_type': MEMBERSHIP_RECORD_TYPE.DIRECT_ADD,
        'granted_at': proposal_row.created_at,
        'granted_by_id': proposal_row.user_id,
        'proposal_id': proposal_row.id,
        'is_uncredited': False,
    }


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
    # Adapts from `proposal` table to an empty `proposal_membership` table.
    conn = op.get_bind()
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(proposal))

    progress = get_progressbar("Proposals", count)
    progress.start()
    proposals = conn.execute(
        sa.select(
            [
                proposal.c.id,
                proposal.c.created_at,
                proposal.c.user_id,
                proposal.c.speaker_id,
            ]
        )
    )

    for counter, row in enumerate(proposals):
        values = membership_values(row)
        if row.speaker_id is None:
            values.update(seq=1, user_id=row.user_id, label=PROPOSING_LABEL)
            conn.execute(proposal_membership.insert().values(values))
        elif row.speaker_id == row.user_id:
            values.update(seq=1, user_id=row.user_id)
            conn.execute(proposal_membership.insert().values(values))
        else:
            values.update(
                seq=1, user_id=row.user_id, is_uncredited=True, label=PROPOSING_LABEL
            )
            conn.execute(proposal_membership.insert().values(values))
            values = membership_values(row)
            values.update(seq=2, user_id=row.speaker_id)
            conn.execute(proposal_membership.insert().values(values))

        progress.update(counter)
    progress.finish()


def downgrade():
    # Removes all items from `proposal_membership` table
    op.execute(proposal_membership.delete())
