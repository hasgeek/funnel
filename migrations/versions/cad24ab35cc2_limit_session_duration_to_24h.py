"""Limit session duration to 24h.

Revision ID: cad24ab35cc2
Revises: 60ee1687f59c
Create Date: 2021-06-09 02:50:38.875251

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column

# revision identifiers, used by Alembic.
revision = 'cad24ab35cc2'
down_revision = '60ee1687f59c'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

start_at = column('start_at', sa.TIMESTAMP)
end_at = column('end_at', sa.TIMESTAMP)


def upgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(
                start_at.is_not(None),
                end_at.is_not(None),
                end_at > start_at,
                end_at <= start_at + sa.text("INTERVAL '1 day'"),
            ),
        ),
    )


def downgrade_() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at > start_at),
        ),
    )
