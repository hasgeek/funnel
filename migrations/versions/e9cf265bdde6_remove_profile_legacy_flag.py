"""Remove Profile.legacy flag.

Revision ID: e9cf265bdde6
Revises: fa05ebecbc0f
Create Date: 2021-05-07 02:44:35.530119

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e9cf265bdde6'
down_revision = 'fa05ebecbc0f'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('profile', 'legacy')


def downgrade():
    op.add_column(
        'profile',
        sa.Column(
            'legacy',
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('profile', 'legacy', server_default=None)
