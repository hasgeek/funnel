"""Add restricted video flag to session model.

Revision ID: ee418ce7d057
Revises: c794b4a3a696
Create Date: 2023-08-07 22:15:58.341778

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ee418ce7d057'
down_revision: str = 'c794b4a3a696'
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
    op.add_column(
        'session',
        sa.Column(
            'is_restricted_video',
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        'session', 'is_restricted_video', server_default=None, nullable=False
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_column('session', 'is_restricted_video')
