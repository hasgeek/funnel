"""Hash check constraint.

Revision ID: 83b6643891ec
Revises: 63c44675b6cd
Create Date: 2023-01-20 01:16:50.246175

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '83b6643891ec'
down_revision: str = '63c44675b6cd'
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
    """Upgrade database bind ''."""
    op.create_check_constraint(
        'phone_number_blake2b160_check',
        'phone_number',
        sa.func.length(sa.sql.column('blake2b160')) == 20,
    )
    op.create_check_constraint(
        'email_address_blake2b160_check',
        'email_address',
        sa.func.length(sa.sql.column('blake2b160')) == 20,
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_constraint('email_address_blake2b160_check', 'email_address', type_='check')
    op.drop_constraint('phone_number_blake2b160_check', 'phone_number', type_='check')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
