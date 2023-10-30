"""Project end_at after start_at.

Revision ID: 5f465411775c
Revises: ee8477fff3a8
Create Date: 2021-06-03 02:46:53.673764

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column

# revision identifiers, used by Alembic.
revision = '5f465411775c'
down_revision = 'ee8477fff3a8'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

start_at = column('start_at', sa.TIMESTAMP)
end_at = column('end_at', sa.TIMESTAMP)


def upgrade() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(  # type: ignore[arg-type]
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at > start_at),
        ),
    )
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(  # type: ignore[arg-type]
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at > start_at),
        ),
    )


def downgrade() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(  # type: ignore[arg-type]
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at >= start_at),
        ),
    )
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(  # type: ignore[arg-type]
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.is_not(None), end_at.is_not(None), end_at >= start_at),
        ),
    )
