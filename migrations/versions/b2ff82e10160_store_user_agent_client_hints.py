"""Store user agent client hints.

Revision ID: b2ff82e10160
Revises: b24cbe67fdae
Create Date: 2024-05-03 20:15:18.822288

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2ff82e10160'
down_revision: str = 'b24cbe67fdae'
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
    with op.batch_alter_table('login_session', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'user_agent_client_hints',
                sa.JSON().with_variant(
                    postgresql.JSONB(astext_type=sa.Text()), 'postgresql'
                ),
                nullable=True,
            )
        )


def downgrade_() -> None:
    """Downgrade default database."""
    with op.batch_alter_table('login_session', schema=None) as batch_op:
        batch_op.drop_column('user_agent_client_hints')
