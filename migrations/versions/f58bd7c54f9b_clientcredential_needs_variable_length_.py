"""ClientCredential needs variable length hashes

Revision ID: f58bd7c54f9b
Revises: 073e7961d5df
Create Date: 2020-06-04 05:06:51.336248

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f58bd7c54f9b'
down_revision = '073e7961d5df'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'auth_client_credential',
        'secret_hash',
        existing_type=sa.String(71),
        type_=sa.Unicode,
    )


def downgrade():
    op.alter_column(
        'auth_client_credential',
        'secret_hash',
        existing_type=sa.Unicode,
        type_=sa.String(71),
    )
