"""Add AccountMembership.is_follower column.

Revision ID: 4eb2369f47f5
Revises: 57488bf1cdc0
Create Date: 2024-04-03 15:38:31.693034

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4eb2369f47f5'
down_revision: str = '57488bf1cdc0'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

account_membership = sa.table(
    'account_membership',
    sa.column('is_admin', sa.Boolean()),
    sa.column('is_follower', sa.Boolean()),
)


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    op.add_column(
        'account_membership',
        sa.Column(
            'is_follower', sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.alter_column('account_membership', 'is_follower', server_default=None)
    op.create_check_constraint(
        'account_membership_admin_or_follower_check',
        'account_membership',
        sa.or_(
            account_membership.c.is_admin.is_(True),
            account_membership.c.is_follower.is_(True),
        ),
    )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('account_membership', schema=None) as batch_op:
        batch_op.drop_constraint(
            'account_membership_admin_or_follower_check', type_='check'
        )
        batch_op.drop_column('is_follower')
