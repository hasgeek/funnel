"""Admin and review teams

Revision ID: 55b1ef63bee
Revises: 18052b0cd282
Create Date: 2014-04-19 19:30:27.529641

"""

# revision identifiers, used by Alembic.
revision = '55b1ef63bee'
down_revision = '18052b0cd282'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.add_column('profile', sa.Column('admin_team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=True))
    op.add_column('proposal_space', sa.Column('admin_team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=True))
    op.add_column('proposal_space', sa.Column('review_team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=True))


def downgrade():
    op.drop_column('proposal_space', 'review_team_id')
    op.drop_column('proposal_space', 'admin_team_id')
    op.drop_column('profile', 'admin_team_id')
