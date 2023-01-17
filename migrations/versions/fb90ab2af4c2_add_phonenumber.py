"""Add PhoneNumber.

Revision ID: fb90ab2af4c2
Revises: 4f805eefa9f4
Create Date: 2023-01-17 22:52:13.062751

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'fb90ab2af4c2'
down_revision: str = '4f805eefa9f4'
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
    op.create_table(
        'phone_number',
        sa.Column('phone', sa.Unicode(), nullable=True),
        sa.Column('blake2b160', sa.LargeBinary(), nullable=False),
        sa.Column('delivery_state', sa.Integer(), nullable=True),
        sa.Column('delivery_state_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('active_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_blocked', sa.Boolean(), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            'is_blocked IS NOT true OR is_blocked IS true AND phone IS NULL',
            name='phone_number_phone_is_blocked_check',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
        sa.UniqueConstraint('blake2b160'),
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_table('phone_number')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
