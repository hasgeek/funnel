"""Rename Concierge to Promoter.

Revision ID: 2cc791c09075
Revises: 3d3df26524b7
Create Date: 2021-02-02 13:28:37.930357

"""

from typing import Optional, Tuple, Union

from alembic import op

# revision identifiers, used by Alembic.
revision = '2cc791c09075'
down_revision = '3d3df26524b7'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.alter_column(
        'project_crew_membership', 'is_concierge', new_column_name='is_promoter'
    )


def downgrade() -> None:
    op.alter_column(
        'project_crew_membership', 'is_promoter', new_column_name='is_concierge'
    )
