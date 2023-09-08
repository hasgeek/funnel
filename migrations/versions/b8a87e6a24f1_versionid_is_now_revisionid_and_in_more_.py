"""Versionid is now Revisionid and in more tables.

Revision ID: b8a87e6a24f1
Revises: 832a4481cda9
Create Date: 2022-12-22 12:13:06.124550

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8a87e6a24f1'
down_revision: str = '832a4481cda9'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    op.alter_column('project', 'versionid', new_column_name='revisionid')
    op.alter_column('session', 'versionid', new_column_name='revisionid')

    op.add_column(
        'comment',
        sa.Column(
            'revisionid', sa.Integer(), nullable=False, server_default=sa.text('1')
        ),
    )
    op.add_column(
        'profile',
        sa.Column(
            'revisionid', sa.Integer(), nullable=False, server_default=sa.text('1')
        ),
    )
    op.add_column(
        'proposal',
        sa.Column(
            'revisionid', sa.Integer(), nullable=False, server_default=sa.text('1')
        ),
    )
    op.alter_column('comment', 'revisionid', server_default=None)
    op.alter_column('profile', 'revisionid', server_default=None)
    op.alter_column('proposal', 'revisionid', server_default=None)


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.alter_column('session', 'revisionid', new_column_name='versionid')
    op.alter_column('project', 'revisionid', new_column_name='versionid')
    op.drop_column('proposal', 'revisionid')
    op.drop_column('profile', 'revisionid')
    op.drop_column('comment', 'revisionid')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
