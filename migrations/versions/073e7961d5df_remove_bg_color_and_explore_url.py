"""Remove bg_color and explore_url.

Revision ID: 073e7961d5df
Revises: 34a95ee0c3a0
Create Date: 2020-05-21 15:48:14.035503

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

revision = '073e7961d5df'
down_revision = '34a95ee0c3a0'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.drop_column('project', 'explore_url')
    op.drop_column('project', 'bg_color')


def downgrade() -> None:
    op.add_column(
        'project',
        sa.Column('bg_color', sa.VARCHAR(length=6), autoincrement=False, nullable=True),
    )
    op.add_column(
        'project',
        sa.Column('explore_url', sa.TEXT(), autoincrement=False, nullable=True),
    )
