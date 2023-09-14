"""Add flag for participant-only livestreams.

Revision ID: d5b374c9e589
Revises: ee418ce7d057
Create Date: 2023-08-10 19:56:09.419445

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd5b374c9e589'
down_revision: str = 'ee418ce7d057'
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
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_restricted_video',
                sa.Boolean(),
                nullable=True,
                server_default=sa.false(),
            )
        )
        batch_op.alter_column(
            'is_restricted_video', nullable=False, server_default=None
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('is_restricted_video')
