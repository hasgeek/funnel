"""Add EmailAddress.

Revision ID: 9333436765cd
Revises: 79719ee38228
Create Date: 2020-06-11 07:31:23.089071

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9333436765cd'
down_revision = '79719ee38228'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.create_table(
        'email_address',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('email', sa.Unicode(), nullable=True),
        sa.Column('domain', sa.Unicode(), nullable=True),
        sa.Column('blake2b160', sa.LargeBinary(), nullable=False),
        sa.Column('blake2b160_canonical', sa.LargeBinary(), nullable=False),
        sa.Column('delivery_state', sa.Integer(), nullable=False),
        sa.Column('delivery_state_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('is_blocked', sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "email IS NULL AND domain IS NULL OR"
            " (email SIMILAR TO '(xn--|%.xn--)%') OR"
            " email ILIKE '%' || replace(replace(domain, '_', '\\_'), '%', '\\%')",
            name='email_address_email_domain_check',
        ),
        sa.CheckConstraint('domain = lower(domain)', name='email_address_domain_check'),
        sa.CheckConstraint(
            'is_blocked IS NOT true OR is_blocked IS true AND email IS NULL',
            name='email_address_email_is_blocked_check',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('blake2b160'),
    )
    op.create_index(
        op.f('ix_email_address_blake2b160_canonical'),
        'email_address',
        ['blake2b160_canonical'],
        unique=False,
    )
    op.create_index(
        op.f('ix_email_address_domain'), 'email_address', ['domain'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_email_address_domain'), table_name='email_address')
    op.drop_index(
        op.f('ix_email_address_blake2b160_canonical'), table_name='email_address'
    )
    op.drop_table('email_address')
