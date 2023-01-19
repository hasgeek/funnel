"""Remove UserPhoneClaim.

Revision ID: 9ad724b3e8cc
Revises: 0fae06340346
Create Date: 2022-07-08 11:01:32.223788

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9ad724b3e8cc'
down_revision = '0fae06340346'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade(engine_name=''):
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name=''):
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_():
    """Remove UserPhoneClaim model."""
    op.drop_index('ix_user_phone_claim_phone', table_name='user_phone_claim')
    op.drop_table('user_phone_claim')


def downgrade_():
    """Restore UserPhoneClaim model."""
    op.create_table(
        'user_phone_claim',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('phone', sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column('gets_text', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column(
            'verification_code',
            sa.VARCHAR(length=4),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'verification_attempts', sa.INTEGER(), autoincrement=False, nullable=False
        ),
        sa.Column('private', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('type', sa.VARCHAR(length=30), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], name='user_phone_claim_user_id_fkey'
        ),
        sa.PrimaryKeyConstraint('id', name='user_phone_claim_pkey'),
        sa.UniqueConstraint(
            'user_id', 'phone', name='user_phone_claim_user_id_phone_key'
        ),
    )
    op.create_index(
        'ix_user_phone_claim_phone', 'user_phone_claim', ['phone'], unique=False
    )
