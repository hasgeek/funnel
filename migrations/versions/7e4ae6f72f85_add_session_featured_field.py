"""add session featured field

Revision ID: 7e4ae6f72f85
Revises: 70ffbc1bcf88
Create Date: 2018-11-19 16:50:43.871239

"""

revision = '7e4ae6f72f85'
down_revision = '70ffbc1bcf88'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('session', sa.Column('is_featured', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_column('session', 'is_featured')
