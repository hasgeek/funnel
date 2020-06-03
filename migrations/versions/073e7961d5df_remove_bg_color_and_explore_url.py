"""remove bg_color and explore_url

Revision ID: 073e7961d5df
Revises: 34a95ee0c3a0
Create Date: 2020-05-21 15:48:14.035503

"""

from alembic import op
import sqlalchemy as sa

revision = '073e7961d5df'
down_revision = '34a95ee0c3a0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('project', 'explore_url')
    op.drop_column('project', 'bg_color')


def downgrade():
    op.add_column(
        'project',
        sa.Column('bg_color', sa.VARCHAR(length=6), autoincrement=False, nullable=True),
    )
    op.add_column(
        'project',
        sa.Column('explore_url', sa.TEXT(), autoincrement=False, nullable=True),
    )
