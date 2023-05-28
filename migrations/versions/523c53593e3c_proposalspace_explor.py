"""ProposalSpace explore URL.

Revision ID: 523c53593e3c
Revises: 14d7082476c0
Create Date: 2014-10-13 13:10:49.917013

"""

# revision identifiers, used by Alembic.
revision = '523c53593e3c'
down_revision = '14d7082476c0'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'proposal_space',
        sa.Column('explore_url', sa.Unicode(length=250), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('proposal_space', 'explore_url')
