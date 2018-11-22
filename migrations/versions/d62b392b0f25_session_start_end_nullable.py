"""session's start end fields are nullable

Revision ID: d62b392b0f25
Revises: d6b1904bea0e
Create Date: 2018-11-22 00:40:37.530856

"""

# revision identifiers, used by Alembic.
revision = 'd62b392b0f25'
down_revision = '07ebe99161d5'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('session', 'end', existing_type=postgresql.TIMESTAMP(), nullable=True)
    op.alter_column('session', 'start', existing_type=postgresql.TIMESTAMP(), nullable=True)
    op.create_check_constraint(u'ck_session_start_end_nullable', 'session',
        u'("start" IS NULL AND "end" IS NULL) OR ("start" IS NOT NULL AND "end" IS NOT NULL)')


def downgrade():
    op.drop_constraint(u'ck_session_start_end_nullable', 'session')
    op.alter_column('session', 'start', existing_type=postgresql.TIMESTAMP(), nullable=False)
    op.alter_column('session', 'end', existing_type=postgresql.TIMESTAMP(), nullable=False)
