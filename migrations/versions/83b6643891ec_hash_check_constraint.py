"""Hash check constraint.

Revision ID: 83b6643891ec
Revises: 63c44675b6cd
Create Date: 2023-01-20 01:16:50.246175

"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '83b6643891ec'
down_revision: str = '63c44675b6cd'
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
    """Upgrade database bind ''."""
    op.create_check_constraint(
        'phone_number_blake2b160_check',
        'phone_number',
        'LENGTH(blake2b160) = 20',
    )
    op.create_check_constraint(
        'email_address_blake2b160_check',
        'email_address',
        'LENGTH(blake2b160) = 20',
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_constraint('email_address_blake2b160_check', 'email_address', type_='check')
    op.drop_constraint('phone_number_blake2b160_check', 'phone_number', type_='check')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
