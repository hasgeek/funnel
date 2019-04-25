"""session speaker

Revision ID: 6f98e24760d
Revises: 58588eba8cb8
Create Date: 2013-11-22 17:28:47.751025

"""

# revision identifiers, used by Alembic.
revision = '6f98e24760d'
down_revision = '58588eba8cb8'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.add_column('session', sa.Column('speaker', sa.Unicode(length=200), nullable=True))


def downgrade():
    op.drop_column('session', 'speaker')
