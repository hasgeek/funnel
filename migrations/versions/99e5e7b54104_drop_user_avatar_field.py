"""Drop user avatar field.

Revision ID: 99e5e7b54104
Revises: ea1ea3b0ff95
Create Date: 2020-08-07 12:10:20.004784

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '99e5e7b54104'
down_revision = 'ea1ea3b0ff95'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.drop_column('user', 'avatar')


def downgrade() -> None:
    op.add_column(
        'user', sa.Column('avatar', sa.TEXT(), autoincrement=False, nullable=True)
    )
