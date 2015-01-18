"""Subspaces

Revision ID: 7cd383925de
Revises: 21a7dfe8ab4d
Create Date: 2015-01-18 23:16:09.790396

"""

# revision identifiers, used by Alembic.
revision = '7cd383925de'
down_revision = '21a7dfe8ab4d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal_space', sa.Column('parent_space_id', sa.Integer(), nullable=True))
    op.create_foreign_key('proposal_space_proposal_space_id_fkey',
        'proposal_space', 'proposal_space', ['parent_space_id'], ['id'])


def downgrade():
    op.drop_constraint('proposal_space_proposal_space_id_fkey', 'proposal_space', type_='foreignkey')
    op.drop_column('proposal_space', 'parent_space_id')
