"""Remove Profile.legacy flag.

Revision ID: e9cf265bdde6
Revises: fa05ebecbc0f
Create Date: 2021-05-07 02:44:35.530119

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e9cf265bdde6'
down_revision = 'fa05ebecbc0f'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_column('profile', 'legacy')


def downgrade() -> None:
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
