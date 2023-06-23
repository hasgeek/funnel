"""Session start and end column names.

Revision ID: 5e06feda611d
Revises: b61a489d34a4
Create Date: 2019-06-26 14:59:43.362731

"""

# revision identifiers, used by Alembic.
revision = '5e06feda611d'
down_revision = 'b61a489d34a4'

import sqlalchemy as sa
from alembic import op


def upgrade() -> None:
    op.alter_column('session', 'start', new_column_name='start_at')
    op.alter_column('session', 'end', new_column_name='end_at')
    op.create_index(op.f('ix_session_start_at'), 'session', ['start_at'], unique=False)
    op.create_index(op.f('ix_session_end_at'), 'session', ['end_at'], unique=False)
    op.execute(
        sa.DDL(
            'ALTER TABLE session RENAME CONSTRAINT session_start_end_check '
            'TO session_start_at_end_at_check'
        )
    )


def downgrade() -> None:
    op.execute(
        sa.DDL(
            'ALTER TABLE session RENAME CONSTRAINT session_start_at_end_at_check '
            'TO session_start_end_check'
        )
    )

    op.drop_index(op.f('ix_session_end_at'), table_name='session')
    op.drop_index(op.f('ix_session_start_at'), table_name='session')
    op.alter_column('session', 'start_at', new_column_name='start')
    op.alter_column('session', 'end_at', new_column_name='end')
