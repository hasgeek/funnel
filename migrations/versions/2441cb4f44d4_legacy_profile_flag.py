"""Legacy profile flag.

Revision ID: 2441cb4f44d4
Revises: d62b392b0f25
Create Date: 2018-11-23 01:36:47.060182

"""

# revision identifiers, used by Alembic.
revision = '2441cb4f44d4'
down_revision = 'd62b392b0f25'

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        'profile',
        sa.Column(
            'legacy',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.alter_column('profile', 'legacy', server_default=None)


def downgrade() -> None:
    op.drop_column('profile', 'legacy')
