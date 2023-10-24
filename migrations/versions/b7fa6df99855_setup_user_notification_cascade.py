"""Setup user_notification cascade.

Revision ID: b7fa6df99855
Revises: 7f8114c73092
Create Date: 2020-08-19 10:34:20.503741

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = 'b7fa6df99855'
down_revision = '7f8114c73092'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_constraint(
        'user_notification_eventid_notification_id_fkey',
        'user_notification',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'user_notification_eventid_notification_id_fkey',
        'user_notification',
        'notification',
        ['eventid', 'notification_id'],
        ['eventid', 'id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(
        'user_notification_eventid_notification_id_fkey',
        'user_notification',
        type_='foreignkey',
    )
    op.create_foreign_key(
        'user_notification_eventid_notification_id_fkey',
        'user_notification',
        'notification',
        ['eventid', 'notification_id'],
        ['eventid', 'id'],
    )
