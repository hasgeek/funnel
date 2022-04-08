"""Track OAuth2 refresh token and expiry.

Revision ID: b7165507d80c
Revises: 0fae06340346
Create Date: 2022-03-15 15:38:33.306920

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b7165507d80c'
down_revision = '0fae06340346'
branch_labels = None
depends_on = None


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
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


def downgrade_():
    op.drop_index(
        op.f('ix_user_externalid_oauth_expires_at'), table_name='user_externalid'
    )
    op.drop_column('user_externalid', 'oauth_expires_at')
    op.drop_column('user_externalid', 'oauth_expires_in')
    op.drop_column('user_externalid', 'oauth_refresh_token')


def upgrade_geoname():
    pass


def downgrade_geoname():
    pass
