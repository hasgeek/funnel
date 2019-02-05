"""draft model

Revision ID: e073be362102
Revises: c3069d33419a
Create Date: 2019-02-05 12:12:21.134284

"""

revision = 'e073be362102'
down_revision = 'c3069d33419a'

from alembic import op
import sqlalchemy as sa

from sqlalchemy_utils.types.uuid import UUIDType
from coaster.sqlalchemy.columns import JsonDict


def upgrade():
    op.create_table('draft',
        sa.Column('table', sa.UnicodeText(), nullable=True),
        sa.Column('table_row_id', UUIDType(binary=False), nullable=True),
        sa.Column('body', JsonDict(), server_default='{}', nullable=False),
        sa.Column('revision', UUIDType(binary=False), nullable=True),
        sa.Column('id', UUIDType(binary=False), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('draft')
