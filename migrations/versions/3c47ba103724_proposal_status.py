# -*- coding: utf-8 -*-

"""Proposal.status

Revision ID: 3c47ba103724
Revises: 6f98e24760d
Create Date: 2014-01-28 00:09:39.231864

"""

# revision identifiers, used by Alembic.
revision = '3c47ba103724'
down_revision = '6f98e24760d'

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa  # NOQA


# The PROPOSALSTATUS class as it was when this migration was created
class PROPOSALSTATUS:  # NOQA
    # Draft-state for future use, so people can save their proposals and submit only when ready
    DRAFT = 0
    SUBMITTED = 1
    CONFIRMED = 2
    REJECTED = 3
    SHORTLISTED = 4
    BACKUP = 5
    CANCELLED = 6


def upgrade():
    connection = op.get_bind()
    proposal = table(
        'proposal', column('confirmed', sa.BOOLEAN()), column('status', sa.Integer)
    )
    connection.execute(
        proposal.update()
        .where(proposal.c.confirmed == True)
        .values({proposal.c.status: PROPOSALSTATUS.CONFIRMED})
    )  # NOQA
    connection.execute(
        proposal.update()
        .where(proposal.c.confirmed == False)
        .values({proposal.c.status: PROPOSALSTATUS.SUBMITTED})
    )  # NOQA
    op.drop_column('proposal', 'confirmed')


def downgrade():
    connection = op.get_bind()
    proposal = table(
        'proposal', column('confirmed', sa.BOOLEAN()), column('status', sa.Integer)
    )
    op.add_column(
        'proposal',
        sa.Column('confirmed', sa.BOOLEAN(), server_default="False", nullable=False),
    )
    connection.execute(
        proposal.update()
        .where(proposal.c.status == PROPOSALSTATUS.CONFIRMED)
        .values({proposal.c.confirmed: True})
    )
    connection.execute(proposal.update().values({proposal.c.status: 0}))
    op.alter_column('proposal', 'confirmed', server_default=None)
