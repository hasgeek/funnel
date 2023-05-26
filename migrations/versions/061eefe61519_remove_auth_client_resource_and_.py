"""Remove auth_client resource and namespace.

Revision ID: 061eefe61519
Revises: d5d6aba41475
Create Date: 2021-05-12 21:09:56.657928

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '061eefe61519'
down_revision = 'd5d6aba41475'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    op.drop_constraint('auth_client_namespace_key', 'auth_client', type_='unique')
    op.drop_column('auth_client', 'namespace')


def downgrade() -> None:
    op.add_column(
        'auth_client',
        sa.Column('namespace', sa.TEXT(), autoincrement=False, nullable=True),
    )
    op.create_unique_constraint(
        'auth_client_namespace_key', 'auth_client', ['namespace']
    )
