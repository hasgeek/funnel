"""Use varchar instead of text for single-line strings.

Revision ID: 6994cbf757ab
Revises: bd377f7c3b3b
Create Date: 2024-03-27 13:20:00.252741

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6994cbf757ab'
down_revision: str = 'bd377f7c3b3b'
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
    """Upgrade default database."""
    with op.batch_alter_table('account_externalid', schema=None) as batch_op:
        batch_op.alter_column(
            'service',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'userid',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'username',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token_secret',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token_type',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_refresh_token',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('auth_client', schema=None) as batch_op:
        batch_op.alter_column(
            'website',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'notification_uri',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'scope', existing_type=sa.TEXT(), type_=sa.Unicode(), existing_nullable=True
        )

    with op.batch_alter_table('auth_client_permissions', schema=None) as batch_op:
        batch_op.alter_column(
            'permissions',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_client_team_permissions', schema=None) as batch_op:
        batch_op.alter_column(
            'permissions',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_code', schema=None) as batch_op:
        batch_op.alter_column(
            'redirect_uri',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'scope',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_token', schema=None) as batch_op:
        batch_op.alter_column(
            'scope',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )

    with op.batch_alter_table('login_session', schema=None) as batch_op:
        batch_op.alter_column(
            'user_agent',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=False,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'livestream_urls',
            existing_type=postgresql.ARRAY(sa.TEXT()),
            type_=sa.ARRAY(sa.Unicode(), dimensions=1),
            existing_nullable=True,
            existing_server_default=sa.text("'{}'::text[]"),  # type: ignore[arg-type]
        )

    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.alter_column(
            'video_id',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'video_source',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.alter_column(
            'video_id',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'video_source',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )

    with op.batch_alter_table('sms_message', schema=None) as batch_op:
        batch_op.alter_column(
            'transactionid',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'fail_reason',
            existing_type=sa.TEXT(),
            type_=sa.Unicode(),
            existing_nullable=True,
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('sms_message', schema=None) as batch_op:
        batch_op.alter_column(
            'fail_reason',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'transactionid',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )

    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.alter_column(
            'video_source',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'video_id',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )

    with op.batch_alter_table('proposal', schema=None) as batch_op:
        batch_op.alter_column(
            'video_source',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'video_id',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )

    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.alter_column(
            'livestream_urls',
            existing_type=sa.ARRAY(sa.Unicode(), dimensions=1),
            type_=postgresql.ARRAY(sa.TEXT()),
            existing_nullable=True,
            existing_server_default=sa.text("'{}'::text[]"),  # type: ignore[arg-type]
        )

    with op.batch_alter_table('login_session', schema=None) as batch_op:
        batch_op.alter_column(
            'user_agent',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_token', schema=None) as batch_op:
        batch_op.alter_column(
            'scope',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_code', schema=None) as batch_op:
        batch_op.alter_column(
            'scope',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'redirect_uri',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_client_team_permissions', schema=None) as batch_op:
        batch_op.alter_column(
            'permissions',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_client_permissions', schema=None) as batch_op:
        batch_op.alter_column(
            'permissions',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('auth_client', schema=None) as batch_op:
        batch_op.alter_column(
            'scope', existing_type=sa.Unicode(), type_=sa.TEXT(), existing_nullable=True
        )
        batch_op.alter_column(
            'notification_uri',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'website',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )

    with op.batch_alter_table('account_externalid', schema=None) as batch_op:
        batch_op.alter_column(
            'oauth_refresh_token',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token_type',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token_secret',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'oauth_token',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'username',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            'userid',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'service',
            existing_type=sa.Unicode(),
            type_=sa.TEXT(),
            existing_nullable=False,
        )
