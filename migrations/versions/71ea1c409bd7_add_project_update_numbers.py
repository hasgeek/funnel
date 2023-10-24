"""Add Project update numbers.

Revision ID: 71ea1c409bd7
Revises: 6d3599c52873
Create Date: 2020-07-27 00:08:46.972049

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '71ea1c409bd7'
down_revision = '6d3599c52873'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column('post', sa.Column('number', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('post', 'number')
