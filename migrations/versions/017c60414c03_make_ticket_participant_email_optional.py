"""Make ticket participant email optional.

Revision ID: 017c60414c03
Revises: 4f9ca10b7b9d
Create Date: 2023-10-05 15:08:34.540672

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '017c60414c03'
down_revision: str = '4f9ca10b7b9d'
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
    with op.batch_alter_table('ticket_participant', schema=None) as batch_op:
        batch_op.alter_column(
            'email_address_id', existing_type=sa.INTEGER(), nullable=True
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('ticket_participant', schema=None) as batch_op:
        batch_op.alter_column(
            'email_address_id', existing_type=sa.INTEGER(), nullable=False
        )
