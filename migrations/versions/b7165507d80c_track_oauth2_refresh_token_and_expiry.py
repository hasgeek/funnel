"""Track OAuth2 refresh token and expiry.

Revision ID: b7165507d80c
Revises: 9ad724b3e8cc
Create Date: 2022-03-15 15:38:33.306920

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b7165507d80c'
down_revision = '9ad724b3e8cc'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name='') -> None:
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    op.add_column(
        'user_externalid',
        sa.Column('oauth_refresh_token', sa.UnicodeText(), nullable=True),
    )
    op.add_column(
        'user_externalid', sa.Column('oauth_expires_in', sa.Integer(), nullable=True)
    )
    op.add_column(
        'user_externalid',
        sa.Column('oauth_expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        op.f('ix_user_externalid_oauth_expires_at'),
        'user_externalid',
        ['oauth_expires_at'],
        unique=False,
    )


def downgrade_() -> None:
    op.drop_index(
        op.f('ix_user_externalid_oauth_expires_at'), table_name='user_externalid'
    )
    op.drop_column('user_externalid', 'oauth_expires_at')
    op.drop_column('user_externalid', 'oauth_expires_in')
    op.drop_column('user_externalid', 'oauth_refresh_token')


def upgrade_geoname() -> None:
    pass


def downgrade_geoname() -> None:
    pass
