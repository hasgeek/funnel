"""Proposal space redirect

Revision ID: 2db4d4be1fdf
Revises: a2115fab4c4
Create Date: 2015-01-16 02:14:52.672861

"""

# revision identifiers, used by Alembic.
revision = '2db4d4be1fdf'
down_revision = 'a2115fab4c4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('proposal_space_redirect',
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.Unicode(length=250), nullable=False),
        sa.Column('proposal_space_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profile.id'], ),
        sa.ForeignKeyConstraint(['proposal_space_id'], ['proposal_space.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('profile_id', 'name')
        )


def downgrade():
    op.drop_table('proposal_space_redirect')
