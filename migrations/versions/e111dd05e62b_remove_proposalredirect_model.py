"""Remove ProposalRedirect model.

Revision ID: e111dd05e62b
Revises: e9cf265bdde6
Create Date: 2021-05-07 02:58:36.527380

"""

from typing import Optional, Tuple, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e111dd05e62b'
down_revision = 'e9cf265bdde6'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade():
    op.drop_table('proposal_redirect')


def downgrade():
    op.create_table(
        'proposal_redirect',
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
        sa.Column('project_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('url_id', sa.INTEGER(), autoincrement=False, nullable=False),
        sa.Column('proposal_id', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ['project_id'], ['project.id'], name='proposal_redirect_project_id_fkey'
        ),
        sa.ForeignKeyConstraint(
            ['proposal_id'],
            ['proposal.id'],
            name='proposal_redirect_proposal_id_fkey',
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('project_id', 'url_id', name='proposal_redirect_pkey'),
    )
