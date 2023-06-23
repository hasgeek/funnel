"""Add Project update numbers.

Revision ID: 71ea1c409bd7
Revises: 6d3599c52873
Create Date: 2020-07-27 00:08:46.972049

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '71ea1c409bd7'
down_revision = '6d3599c52873'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.add_column('post', sa.Column('number', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('post', 'number')
