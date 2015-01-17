"""Use CoordinatesMixin

Revision ID: 2a5516432f66
Revises: 2db4d4be1fdf
Create Date: 2015-01-17 12:16:51.529610

"""

# revision identifiers, used by Alembic.
revision = '2a5516432f66'
down_revision = '2db4d4be1fdf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('venue', 'latitude', existing_type=sa.Numeric(8, 5), type_=sa.Numeric())
    op.alter_column('venue', 'longitude', existing_type=sa.Numeric(8, 5), type_=sa.Numeric())


def downgrade():
    op.alter_column('venue', 'latitude', existing_type=sa.Numeric(), type_=sa.Numeric(8, 5))
    op.alter_column('venue', 'longitude', existing_type=sa.Numeric(), type_=sa.Numeric(8, 5))
