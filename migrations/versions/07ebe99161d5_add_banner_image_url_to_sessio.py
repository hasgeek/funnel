"""Add banner_image_url field to session.

Revision ID: 07ebe99161d5
Revises: 60a132ae73f1
Create Date: 2018-11-21 19:06:35.140390

"""

# revision identifiers, used by Alembic.
revision = '07ebe99161d5'
down_revision = '60a132ae73f1'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.add_column(
        'session', sa.Column('banner_image_url', sa.Unicode(length=2000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('session', 'banner_image_url')
