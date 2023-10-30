"""Add label to project crew membership.

Revision ID: d0a6fab28b7f
Revises: 7aa9eb80aab4
Create Date: 2023-03-15 01:37:55.947574

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd0a6fab28b7f'
down_revision: str = '7aa9eb80aab4'
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
    with op.batch_alter_table('project_crew_membership', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'label',
                sa.Unicode(),
                sa.CheckConstraint(
                    "label <> ''", name='project_crew_membership_label_check'
                ),
                nullable=True,
            )
        )


def downgrade_() -> None:
    """Downgrade database bind ''."""
    with op.batch_alter_table('project_crew_membership', schema=None) as batch_op:
        batch_op.drop_column('label')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
