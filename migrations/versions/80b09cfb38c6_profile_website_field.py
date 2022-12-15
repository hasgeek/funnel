"""Profile website field.

Revision ID: 80b09cfb38c6
Revises: 99e5e7b54104
Create Date: 2020-08-06 15:18:01.978252

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

from coaster.sqlalchemy import UrlType

# revision identifiers, used by Alembic.
revision = '80b09cfb38c6'
down_revision = '99e5e7b54104'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.add_column('profile', sa.Column('website', UrlType(), nullable=True))


def downgrade():
    op.drop_column('profile', 'website')
