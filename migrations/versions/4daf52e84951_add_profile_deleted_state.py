"""Add profile deleted state.

Revision ID: 4daf52e84951
Revises: b7165507d80c
Create Date: 2022-07-09 00:00:42.949382

"""

from typing import Optional, Tuple, Union

from alembic import op

# revision identifiers, used by Alembic.
revision = '4daf52e84951'
down_revision = 'b7165507d80c'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Add profile deleted state."""
    op.drop_constraint('profile_state_check', 'profile', type_='check')
    op.create_check_constraint(
        'profile_state_check', 'profile', 'state IN (0, 1, 2, 3)'
    )


def downgrade_() -> None:
    """Remove profile deleted state."""
    op.drop_constraint('profile_state_check', 'profile', type_='check')
    op.create_check_constraint('profile_state_check', 'profile', 'state IN (0, 1, 2)')
