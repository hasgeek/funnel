"""Proposal redirects

Revision ID: 21a7dfe8ab4d
Revises: 2a5516432f66
Create Date: 2015-01-17 19:30:22.036714

"""

# revision identifiers, used by Alembic.
revision = '21a7dfe8ab4d'
down_revision = '2a5516432f66'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('proposal_redirect',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=False),
        sa.Column('url_id', sa.Integer(), nullable=False),
        sa.Column('proposal_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposal.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ),
        sa.PrimaryKeyConstraint('proposal_space_id', 'url_id')
        )


def downgrade():
    op.drop_table('proposal_redirect')
