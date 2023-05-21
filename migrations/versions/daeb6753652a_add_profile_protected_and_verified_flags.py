"""Add profile protected and verified flags.

Revision ID: daeb6753652a
Revises: 8b46a8a8ca17
Create Date: 2020-11-06 02:57:05.891627

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'daeb6753652a'
down_revision = '8b46a8a8ca17'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.add_column(
        'profile',
        sa.Column(
            'is_protected',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('profile', 'is_protected', server_default=None)
    op.add_column(
        'profile',
        sa.Column(
            'is_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.sql.expression.false(),
        ),
    )
    op.alter_column('profile', 'is_verified', server_default=None)
    op.create_index(
        op.f('ix_profile_is_verified'), 'profile', ['is_verified'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_profile_is_verified'), table_name='profile')
    op.drop_column('profile', 'is_verified')
    op.drop_column('profile', 'is_protected')
