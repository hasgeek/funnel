"""removed date, date_upto from project

Revision ID: c11dc931b903
Revises: 752dee4ae101
Create Date: 2019-06-08 10:58:13.772112

"""

# revision identifiers, used by Alembic.
revision = 'c11dc931b903'
down_revision = '752dee4ae101'

from alembic import op
import sqlalchemy as sa  # NOQA


def upgrade():
    op.drop_column('project', 'date')
    op.drop_column('project', 'date_upto')


def downgrade():
    op.add_column('project', sa.Column('date_upto', sa.DATE(), autoincrement=False, nullable=True))
    op.add_column('project', sa.Column('date', sa.DATE(), autoincrement=False, nullable=True))
