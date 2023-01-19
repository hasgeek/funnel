"""Add version numbers for timestamped models.

Revision ID: 0fae06340346
Revises: 277ba2ca9e3e
Create Date: 2022-01-06 16:11:26.035319

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0fae06340346'
down_revision = '277ba2ca9e3e'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade(engine_name=''):
    # Do not modify. Edit `upgrade_` instead
    globals().get('upgrade_%s' % engine_name, lambda: None)()


def downgrade(engine_name=''):
    # Do not modify. Edit `downgrade_` instead
    globals().get('downgrade_%s' % engine_name, lambda: None)()


def upgrade_():
    op.add_column(
        'project',
        sa.Column(
            'versionid', sa.Integer(), nullable=False, server_default=sa.text('1')
        ),
    )
    op.add_column(
        'session',
        sa.Column(
            'versionid', sa.Integer(), nullable=False, server_default=sa.text('1')
        ),
    )
    op.alter_column('project', 'versionid', server_default=None)
    op.alter_column('session', 'versionid', server_default=None)


def downgrade_():
    op.drop_column('session', 'versionid')
    op.drop_column('project', 'versionid')


def upgrade_geoname():
    pass


def downgrade_geoname():
    pass
