"""Team.public flag.

Revision ID: 0d462811a07f
Revises: 71ea1c409bd7
Create Date: 2020-07-29 04:01:40.257520

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0d462811a07f'
down_revision = '71ea1c409bd7'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'team',
        sa.Column(
            'is_public',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('team', 'is_public', server_default=None)


def downgrade() -> None:
    op.drop_column('team', 'is_public')
