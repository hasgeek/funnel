"""Add sysadmin flag.

Revision ID: 7aa9eb80aab4
Revises: 2151c9f8e955
Create Date: 2023-03-08 22:10:27.937483

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7aa9eb80aab4'
down_revision: str = '2151c9f8e955'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


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
    with op.batch_alter_table('site_membership', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_sysadmin',
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            )
        )
        batch_op.alter_column('is_sysadmin', server_default=None)
        batch_op.drop_constraint('site_membership_has_role', type_='check')
        batch_op.create_check_constraint(
            'site_membership_has_role',
            'is_comment_moderator IS true OR is_user_moderator IS true'
            ' OR is_site_editor IS true OR is_sysadmin IS true',
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('site_membership', schema=None) as batch_op:
        batch_op.drop_constraint('site_membership_has_role', type_='check')
        batch_op.create_check_constraint(
            'site_membership_has_role',
            'is_comment_moderator IS true OR is_user_moderator IS true'
            ' OR is_site_editor IS true',
        )
        batch_op.drop_column('is_sysadmin')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
