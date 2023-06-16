"""Add inherit sections to proposal space.

Revision ID: 3b189f2e5c56
Revises: 416a2f958279
Create Date: 2015-12-29 13:04:34.484205

"""

# revision identifiers, used by Alembic.
revision = '3b189f2e5c56'
down_revision = '416a2f958279'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        'proposal_space',
        sa.Column(
            'inherit_sections', sa.Boolean(), nullable=False, server_default='True'
        ),
    )


def downgrade() -> None:
    op.drop_column('proposal_space', 'inherit_sections')
