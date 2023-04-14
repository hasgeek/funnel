"""Add start/end check constraints.

Revision ID: a5dbb3f843e4
Revises: 08cef852ca39
Create Date: 2021-04-27 17:38:26.162336

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.sql import column
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a5dbb3f843e4'
down_revision = '08cef852ca39'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None

start_at = column('start_at', sa.TIMESTAMP)
end_at = column('end_at', sa.TIMESTAMP)


def upgrade():
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at >= start_at),
        ),
    )
    op.create_check_constraint(
        'project_start_at_end_at_check',
        'project',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None), end_at >= start_at),
        ),
    )


def downgrade():
    op.drop_constraint('project_start_at_end_at_check', 'project', type_='check')
    op.drop_constraint('session_start_at_end_at_check', 'session', type_='check')
    op.create_check_constraint(
        'session_start_at_end_at_check',
        'session',
        sa.or_(
            sa.and_(start_at.is_(None), end_at.is_(None)),
            sa.and_(start_at.isnot(None), end_at.isnot(None)),
        ),
    )
