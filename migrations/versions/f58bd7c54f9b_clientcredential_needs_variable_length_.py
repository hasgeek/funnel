"""ClientCredential needs variable length hashes.

Revision ID: f58bd7c54f9b
Revises: 073e7961d5df
Create Date: 2020-06-04 05:06:51.336248

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f58bd7c54f9b'
down_revision = '073e7961d5df'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.alter_column(
        'auth_client_credential',
        'secret_hash',
        existing_type=sa.String(71),
        type_=sa.Unicode,
    )


def downgrade() -> None:
    op.alter_column(
        'auth_client_credential',
        'secret_hash',
        existing_type=sa.Unicode,
        type_=sa.String(71),
    )
