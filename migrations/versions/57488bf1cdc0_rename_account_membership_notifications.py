"""Rename account_membership notifications.

Revision ID: 57488bf1cdc0
Revises: ebc3c332a7c8
Create Date: 2024-03-28 00:49:01.882519

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '57488bf1cdc0'
down_revision: str = 'ebc3c332a7c8'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

notification = sa.table(
    'notification',
    sa.column('type', sa.String()),
)
notification_preferences = sa.table(
    'notification_preferences',
    sa.column('notification_type', sa.String()),
)

renames = [
    ('organization_membership_granted', 'account_admin'),
    ('organization_membership_revoked', 'account_admin_revoked'),
    ('project_crew_membership_granted', 'project_crew'),
    ('project_crew_membership_revoked', 'project_crew_revoked'),
]


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
    for old_name, new_name in renames:
        op.execute(
            notification.update()
            .values(type=new_name)
            .where(notification.c.type == old_name)
        )
        op.execute(
            notification_preferences.update()
            .values(notification_type=new_name)
            .where(notification_preferences.c.notification_type == old_name)
        )


def downgrade_() -> None:
    """Downgrade default database."""
    for old_name, new_name in renames:
        op.execute(
            notification.update()
            .values(type=old_name)
            .where(notification.c.type == new_name)
        )
        op.execute(
            notification_preferences.update()
            .values(notification_type=old_name)
            .where(notification_preferences.c.notification_type == new_name)
        )
