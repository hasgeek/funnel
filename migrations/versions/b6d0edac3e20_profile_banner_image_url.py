"""profile banner image url

Revision ID: b6d0edac3e20
Revises: e3b3ccbca3b9
Create Date: 2020-06-19 12:30:25.891325

"""

from alembic import op
import sqlalchemy as sa

from coaster.sqlalchemy import UrlType

# revision identifiers, used by Alembic.
revision = 'b6d0edac3e20'
down_revision = 'e3b3ccbca3b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('profile', sa.Column('banner_image_url', UrlType(), nullable=True))


def downgrade():
    op.drop_column('profile', 'banner_image_url')
