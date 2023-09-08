"""Update comment notification preferences.

Revision ID: 3847982f1472
Revises: 1bd91b02ced3
Create Date: 2020-09-18 03:27:44.871342

"""

from alembic import op
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = '3847982f1472'
down_revision = '1bd91b02ced3'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

notification_preferences = table(
    'notification_preferences',
    column('notification_type'),
)


def upgrade() -> None:
    op.execute(
        notification_preferences.update()
        .values(notification_type='comment_new')
        .where(notification_preferences.c.notification_type == 'comment_project')
    )

    op.execute(
        notification_preferences.delete().where(
            notification_preferences.c.notification_type == 'comment_proposal'
        )
    )


def downgrade() -> None:
    op.execute(
        notification_preferences.update()
        .values(notification_type='comment_project')
        .where(notification_preferences.c.notification_type == 'comment_new')
    )
