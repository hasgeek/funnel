"""Add start/end check constraints.

Revision ID: a5dbb3f843e4
Revises: 08cef852ca39
Create Date: 2021-04-27 17:38:26.162336

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column

# revision identifiers, used by Alembic.
revision = 'a5dbb3f843e4'
down_revision = '08cef852ca39'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

start_at = column('start_at', sa.TIMESTAMP)
end_at = column('end_at', sa.TIMESTAMP)


def upgrade() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at >= start_at),
        ),
    )
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at >= start_at),
        ),
    )


def downgrade() -> None:
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None)),
        ),
    )
