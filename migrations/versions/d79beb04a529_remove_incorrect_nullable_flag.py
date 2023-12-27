"""Remove incorrect nullable flag.

Revision ID: d79beb04a529
Revises: f0ed25eed4bc
Create Date: 2023-12-21 00:55:05.801455

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd79beb04a529'
down_revision: str = 'f0ed25eed4bc'
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
    with op.batch_alter_table('auth_client', schema=None) as batch_op:
        batch_op.alter_column('account_id', existing_type=sa.INTEGER(), nullable=False)


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('auth_client', schema=None) as batch_op:
        batch_op.alter_column('account_id', existing_type=sa.INTEGER(), nullable=True)
