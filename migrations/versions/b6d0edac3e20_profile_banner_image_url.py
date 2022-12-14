"""profile banner image url.

Revision ID: b6d0edac3e20
Revises: e3b3ccbca3b9
Create Date: 2020-06-19 12:30:25.891325

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

from coaster.sqlalchemy import UrlType

# revision identifiers, used by Alembic.
revision = 'b6d0edac3e20'
down_revision = 'e3b3ccbca3b9'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.add_column('profile', sa.Column('banner_image_url', UrlType(), nullable=True))


def downgrade():
    op.drop_column('profile', 'banner_image_url')
