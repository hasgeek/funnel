"""Add User.locale and auto timezone.

Revision ID: 7f6f417dad02
Revises: 80b09cfb38c6
Create Date: 2020-08-17 07:22:09.637346

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import LocaleType

# revision identifiers, used by Alembic.
revision = '7f6f417dad02'
down_revision = '80b09cfb38c6'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        'user',
        sa.Column(
            'auto_timezone',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.add_column('user', sa.Column('locale', LocaleType(), nullable=True))
    op.add_column(
        'user',
        sa.Column(
            'auto_locale',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.alter_column('user', 'auto_timezone', server_default=None)
    op.alter_column('user', 'auto_locale', server_default=None)


def downgrade() -> None:
    op.drop_column('user', 'auto_locale')
    op.drop_column('user', 'locale')
    op.drop_column('user', 'auto_timezone')
