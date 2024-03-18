"""Add json field 'form' to RSVP.

Revision ID: 1d5e1a11661a
Revises: d0a6fab28b7f
Create Date: 2023-03-17 23:55:04.066491

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '1d5e1a11661a'
down_revision: str = 'd0a6fab28b7f'
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
    with op.batch_alter_table('rsvp', schema=None) as batch_op:
        batch_op.add_column(sa.Column('form', JSONB, nullable=True))


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('rsvp', schema=None) as batch_op:
        batch_op.drop_column('form')
