"""Tagline for Profile.

Revision ID: 832a4481cda9
Revises: 6d031c17a6ee
Create Date: 2022-07-14 13:34:38.590945

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '832a4481cda9'
down_revision: str = '6d031c17a6ee'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    op.add_column('profile', sa.Column('tagline', sa.Unicode(), nullable=True))


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_column('profile', 'tagline')
