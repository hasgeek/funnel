"""Update visibility state change.

Revision ID: 0afd20b31eb6
Revises: 16c4e4bc3fe0
Create Date: 2024-03-12 14:36:01.196118

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0afd20b31eb6'
down_revision: str = '16c4e4bc3fe0'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

update = sa.table('update', sa.column('visibility_state'))


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
    op.drop_constraint('update_visibility_state_check', 'update', type_='check')
    op.create_check_constraint(
        'update_visibility_state_check',
        'update',
        update.c.visibility_state.in_([1, 2, 3]),
    )


def downgrade_() -> None:
    """Downgrade default database."""
    op.drop_constraint('update_visibility_state_check', 'update', type_='check')
    op.create_check_constraint(
        'update_visibility_state_check',
        'update',
        update.c.visibility_state.in_([1, 2]),
    )
