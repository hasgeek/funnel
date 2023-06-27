"""Fix membership granted_by.

Revision ID: d0097ec29880
Revises: bd465803af3a
Create Date: 2021-04-22 05:20:50.774828

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd0097ec29880'
down_revision = 'bd465803af3a'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.alter_column(
        'commentset_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        'proposal_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        'site_membership', 'granted_by_id', existing_type=sa.INTEGER(), nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        'site_membership', 'granted_by_id', existing_type=sa.INTEGER(), nullable=True
    )
    op.alter_column(
        'proposal_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        'commentset_membership',
        'granted_by_id',
        existing_type=sa.INTEGER(),
        nullable=True,
    )
