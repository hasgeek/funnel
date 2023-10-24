"""Remove proposal feedback model.

Revision ID: 64f0cfe37976
Revises: baf3d9aab272
Create Date: 2021-04-28 02:37:36.369238

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '64f0cfe37976'
down_revision = 'baf3d9aab272'
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.drop_table('proposal_feedback')


def downgrade() -> None:
    op.create_table(
        'proposal_feedback',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            'created_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column('proposal_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('auth_type', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column(
            'id_type', sa.VARCHAR(length=80), autoincrement=False, nullable=False
        ),
        sa.Column('userid', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
        sa.Column('min_scale', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('max_scale', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('content', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('presentation', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ['proposal_id'], ['proposal.id'], name='proposal_feedback_proposal_id_fkey'
        ),
        sa.PrimaryKeyConstraint('id', name='proposal_feedback_pkey'),
        sa.UniqueConstraint(
            'proposal_id',
            'auth_type',
            'id_type',
            'userid',
            name='proposal_feedback_proposal_id_auth_type_id_type_userid_key',
        ),
    )
