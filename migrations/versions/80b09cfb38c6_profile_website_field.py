"""Profile website field.

Revision ID: 80b09cfb38c6
Revises: 99e5e7b54104
Create Date: 2020-08-06 15:18:01.978252

"""

import sqlalchemy as sa
from alembic import op

from coaster.sqlalchemy import UrlType

# revision identifiers, used by Alembic.
revision = '80b09cfb38c6'
down_revision = '99e5e7b54104'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column('profile', sa.Column('website', UrlType(), nullable=True))


def downgrade() -> None:
    op.drop_column('profile', 'website')
