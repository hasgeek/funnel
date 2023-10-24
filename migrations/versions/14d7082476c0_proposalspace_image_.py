"""ProposalSpace image and color.

Revision ID: 14d7082476c0
Revises: 577689971aa0
Create Date: 2014-10-12 17:57:10.723917

"""

# revision identifiers, used by Alembic.
revision = '14d7082476c0'
down_revision = '577689971aa0'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        'proposal_space', sa.Column('bg_color', sa.Unicode(length=6), nullable=True)
    )
    op.add_column(
        'proposal_space', sa.Column('bg_image', sa.Unicode(length=250), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('proposal_space', 'bg_image')
    op.drop_column('proposal_space', 'bg_color')
