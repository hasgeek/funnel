"""drop user avatar field

Revision ID: 99e5e7b54104
Revises: dcd0870c24cc
Create Date: 2020-08-07 12:10:20.004784

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '99e5e7b54104'
down_revision = 'ea1ea3b0ff95'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('user', 'avatar')


def downgrade():
    op.add_column(
        'user', sa.Column('avatar', sa.TEXT(), autoincrement=False, nullable=True)
    )
