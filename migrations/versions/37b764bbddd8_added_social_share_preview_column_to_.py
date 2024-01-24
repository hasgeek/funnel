"""Add preview_image column to Project model.

Revision ID: 37b764bbddd8
Revises: 017c60414c03
Create Date: 2023-10-13 20:08:06.483116

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '37b764bbddd8'
down_revision: str = '017c60414c03'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(sa.Column('preview_image', sa.LargeBinary(), nullable=True))


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('preview_image')
