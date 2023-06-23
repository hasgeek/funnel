"""Project cfp_end_at after cfp_start_at.

Revision ID: 60ee1687f59c
Revises: 5f465411775c
Create Date: 2021-06-03 15:34:31.913604

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column

cfp_start_at = column('start_at', sa.TIMESTAMP)
cfp_end_at = column('end_at', sa.TIMESTAMP)

# revision identifiers, used by Alembic.
revision = '60ee1687f59c'
down_revision = '5f465411775c'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.create_check_constraint(
        'project_cfp_start_at_cfp_end_at_check',
        'project',
        sa.or_(
            sa.and_(cfp_start_at.is_(None), cfp_end_at.is_(None)),
            sa.and_(cfp_start_at.is_not(None), cfp_end_at.is_(None)),
            sa.and_(
                cfp_start_at.is_not(None),
                cfp_end_at.is_not(None),
                cfp_end_at > cfp_start_at,
            ),
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        'project_cfp_start_at_cfp_end_at_check', 'project', type_='check'
    )
