"""project location field

Revision ID: 92e1cc95c7f7
Revises: 2441cb4f44d4
Create Date: 2018-11-24 08:27:06.710711

"""

revision = '92e1cc95c7f7'
down_revision = '2441cb4f44d4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('project', sa.Column('location', sa.Unicode(length=50), nullable=True))


def downgrade():
    op.drop_column('project', 'location')
