"""Add AccountMembership.label field.

Revision ID: 9ada98ef2f2d
Revises: e63eeea663e8
Create Date: 2024-03-27 20:55:36.484352

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9ada98ef2f2d'
down_revision: str = 'e63eeea663e8'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    with op.batch_alter_table('account_membership', schema=None) as batch_op:
        batch_op.add_column(sa.Column('label', sa.String(), nullable=True))


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('account_membership', schema=None) as batch_op:
        batch_op.drop_column('label')
