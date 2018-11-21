"""add banner_image_url field to session

Revision ID: 07ebe99161d5
Revises: d6b1904bea0e
Create Date: 2018-11-21 19:06:35.140390

"""

# revision identifiers, used by Alembic.
revision = '07ebe99161d5'
down_revision = 'd6b1904bea0e'

from alembic import op
import sqlalchemy as sa



def upgrade():
    op.add_column('session', sa.Column('banner_image_url', sa.Unicode(length=250), nullable=True))


def downgrade():
    op.drop_column('session', 'banner_image_url')
