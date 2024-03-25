"""Update notification data.

Revision ID: bd377f7c3b3b
Revises: 0afd20b31eb6
Create Date: 2024-03-22 18:28:50.178325

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bd377f7c3b3b'
down_revision: str = '0afd20b31eb6'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


notification = sa.table(
    'notification',
    sa.column('type', sa.Unicode()),
    sa.column('document_uuid', sa.Uuid()),
    sa.column('fragment_uuid', sa.Uuid()),
)
project = sa.table(
    'project',
    sa.column('id', sa.Integer()),
    sa.column('uuid', sa.Uuid()),
)
update = sa.table(
    'update',
    sa.column('id', sa.Integer()),
    sa.column('uuid', sa.Uuid()),
    sa.column('project_id', sa.Integer()),
)


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
    # Rename type for update notification, move update UUID from document to fragment,
    # and insert project UUID as document
    op.execute(
        notification.update()
        .values(
            type='project_update',
            document_uuid=project.c.uuid,
            fragment_uuid=update.c.uuid,
        )
        .where(
            notification.c.type == 'update_new',
            notification.c.document_uuid == update.c.uuid,
            update.c.project_id == project.c.id,
        )
    )


def downgrade_() -> None:
    """Downgrade default database."""
    # Restore old notification type name, move update UUID from fragment to document,
    # and set fragment to None
    op.execute(
        notification.update()
        .values(
            type='update_new',
            document_uuid=notification.c.fragment_uuid,
            fragment_uuid=None,
        )
        .where(notification.c.type == 'project_update')
    )
