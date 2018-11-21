"""session's start end fields are nullable

Revision ID: d62b392b0f25
Revises: d6b1904bea0e
Create Date: 2018-11-22 00:40:37.530856

"""

# revision identifiers, used by Alembic.
revision = 'd62b392b0f25'
down_revision = 'd6b1904bea0e'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('session', 'end', existing_type=postgresql.TIMESTAMP(), nullable=True)
    op.alter_column('session', 'start', existing_type=postgresql.TIMESTAMP(), nullable=True)


def downgrade():
    op.alter_column('session', 'start', existing_type=postgresql.TIMESTAMP(), nullable=False)
    op.alter_column('session', 'end', existing_type=postgresql.TIMESTAMP(), nullable=False)
