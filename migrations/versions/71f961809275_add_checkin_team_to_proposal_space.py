# -*- coding: utf-8 -*-

"""add_checkin_team_to_proposal_space

Revision ID: 71f961809275
Revises: 90cc904ece17
Create Date: 2018-04-20 00:57:52.673419

"""

# revision identifiers, used by Alembic.
revision = '71f961809275'
down_revision = '90cc904ece17'

import sqlalchemy as sa  # NOQA
from alembic import op


def upgrade():
    op.add_column(
        'proposal_space',
        sa.Column(
            'checkin_team_id', sa.Integer(), sa.ForeignKey('team.id'), nullable=True
        ),
    )


def downgrade():
    op.drop_column('proposal_space', 'checkin_team_id')
