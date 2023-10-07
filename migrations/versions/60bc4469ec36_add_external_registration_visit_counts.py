"""Add external registration visit counts.

Revision ID: 60bc4469ec36
Revises: 017c60414c03
Create Date: 2023-09-20 15:35:34.613245

"""


import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '60bc4469ec36'
down_revision: str = '017c60414c03'
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
    """Upgrade default database."""
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('buy_tickets_visits_anon', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('buy_tickets_visits_auth', sa.Integer(), nullable=True)
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('project', schema=None) as batch_op:
        batch_op.drop_column('buy_tickets_visits_auth')
        batch_op.drop_column('buy_tickets_visits_anon')
