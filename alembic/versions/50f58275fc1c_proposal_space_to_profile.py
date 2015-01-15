"""Proposal space to profile

Revision ID: 50f58275fc1c
Revises: 50a8f43b4e5f
Create Date: 2015-01-15 21:21:34.334652

"""

# revision identifiers, used by Alembic.
revision = '50f58275fc1c'
down_revision = '50a8f43b4e5f'

from alembic import op


def upgrade():
    op.create_foreign_key('proposal_space_profile_id_fkey', 'proposal_space', 'profile', ['profile_id'], ['id'])


def downgrade():
    op.drop_constraint('proposal_space_profile_id_fkey', 'proposal_space', type_='foreignkey')
