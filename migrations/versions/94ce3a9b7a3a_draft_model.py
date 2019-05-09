"""draft model

Revision ID: 94ce3a9b7a3a
Revises: c3069d33419a
Create Date: 2019-02-06 20:48:34.700795

"""

revision = '94ce3a9b7a3a'
down_revision = 'a9cb0e1c52ed'

from alembic import op
import sqlalchemy as sa  # NOQA

from sqlalchemy_utils.types.uuid import UUIDType
from coaster.sqlalchemy.columns import JsonDict


def upgrade():
    op.create_table('draft',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('table', sa.UnicodeText(), nullable=False),
        sa.Column('table_row_id', UUIDType(binary=False), nullable=False),
        sa.Column('body', JsonDict(), server_default='{}', nullable=False),
        sa.Column('revision', UUIDType(binary=False), nullable=True),
        sa.PrimaryKeyConstraint('table', 'table_row_id')
        )


def downgrade():
    op.drop_table('draft')
