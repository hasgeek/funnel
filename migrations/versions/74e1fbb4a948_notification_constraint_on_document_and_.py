"""Notification constraint on document and fragment.

Revision ID: 74e1fbb4a948
Revises: c47007758ee6
Create Date: 2020-08-29 17:59:31.485184

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '74e1fbb4a948'
down_revision = 'c47007758ee6'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_index(
        'notification_type_document_uuid_fragment_uuid_key',
        'notification',
        ['type', 'document_uuid', 'fragment_uuid'],
        unique=True,
        postgresql_where=sa.text('fragment_uuid IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index(
        'notification_type_document_uuid_fragment_uuid_key', table_name='notification'
    )
