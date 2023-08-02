"""Add PhoneNumber.

Revision ID: fb90ab2af4c2
Revises: 4f805eefa9f4
Create Date: 2023-01-17 22:52:13.062751

"""

from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

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
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('number', sa.Unicode(), nullable=True),
        sa.Column('blake2b160', sa.LargeBinary(), nullable=False),
        sa.Column('allow_sms', sa.Boolean(), nullable=False),
        sa.Column('allow_wa', sa.Boolean(), nullable=False),
        sa.Column('allow_sm', sa.Boolean(), nullable=False),
        sa.Column('msg_sms_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_sms_delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_sms_failed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_wa_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_wa_delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_wa_failed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_sm_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_sm_delivered_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('msg_sm_failed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('active_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('blocked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            'blocked_at IS NULL OR blocked_at IS NOT NULL AND number IS NULL',
            name='phone_number_blocked_at_number_check',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number'),
        sa.UniqueConstraint('blake2b160'),
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_table('phone_number')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
