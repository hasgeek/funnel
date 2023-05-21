"""Project end_at after start_at.

Revision ID: 5f465411775c
Revises: ee8477fff3a8
Create Date: 2021-06-03 02:46:53.673764

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.sql import column
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5f465411775c'
down_revision = 'ee8477fff3a8'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

start_at = column('start_at', sa.TIMESTAMP)
end_at = column('end_at', sa.TIMESTAMP)


def upgrade() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at > start_at),
        ),
    )
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at > start_at),
        ),
    )


def downgrade() -> None:
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at >= start_at),
        ),
    )
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at >= start_at),
        ),
    )
