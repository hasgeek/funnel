"""Add has membership flag to project model.

Revision ID: 00e91a293923
Revises: 4f9ca10b7b9d
Create Date: 2023-09-11 15:34:49.993168

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '00e91a293923'
down_revision: str = '4f9ca10b7b9d'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


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
        'project',
        sa.Column(
            'has_membership',
            sa.Boolean(),
            nullable=True,
            server_default=sa.false(),
        ),
    )
    op.alter_column(
        'project', 'has_membership', server_default=None, nullable=False
    )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    op.drop_column('session', 'has_membership')

