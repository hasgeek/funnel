"""Fix column lengths.

Revision ID: 530c22761e27
Revises: e2b28adfa135
Create Date: 2020-04-20 16:19:22.597712

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '530c22761e27'
down_revision = 'e2b28adfa135'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.alter_column(
        'profile', 'name', existing_type=sa.Unicode(250), type_=sa.Unicode(63)
    )
    op.alter_column(
        'user', 'timezone', existing_type=sa.Unicode(40), type_=sa.Unicode(50)
    )


def downgrade() -> None:
    op.alter_column(
        'user', 'timezone', existing_type=sa.Unicode(50), type_=sa.Unicode(40)
    )
    op.alter_column(
        'profile', 'name', existing_type=sa.Unicode(63), type_=sa.Unicode(250)
    )
