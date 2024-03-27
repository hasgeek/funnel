"""profile banner image url.

Revision ID: b6d0edac3e20
Revises: e3b3ccbca3b9
Create Date: 2020-06-19 12:30:25.891325

"""

import sqlalchemy as sa
from alembic import op

from coaster.sqlalchemy import UrlType

# revision identifiers, used by Alembic.
revision = 'b6d0edac3e20'
down_revision = 'e3b3ccbca3b9'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column('profile', sa.Column('banner_image_url', UrlType(), nullable=True))


def downgrade() -> None:
    op.drop_column('profile', 'banner_image_url')
