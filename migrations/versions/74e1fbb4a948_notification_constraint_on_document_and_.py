"""Notification constraint on document and fragment.

Revision ID: 74e1fbb4a948
Revises: c47007758ee6
Create Date: 2020-08-29 17:59:31.485184

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '74e1fbb4a948'
down_revision = 'c47007758ee6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'notification_type_document_uuid_fragment_uuid_key',
        'notification',
        ['type', 'document_uuid', 'fragment_uuid'],
        unique=True,
        postgresql_where=sa.text('fragment_uuid IS NOT NULL'),
    )


def downgrade():
    op.drop_index(
        'notification_type_document_uuid_fragment_uuid_key', table_name='notification'
    )
