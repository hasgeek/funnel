"""Set null constraint

Revision ID: 1c496c114b6
Revises: 7cd383925de
Create Date: 2015-01-27 02:09:54.317004

"""

# revision identifiers, used by Alembic.
revision = '1c496c114b6'
down_revision = '7cd383925de'

from alembic import op


def upgrade():
    op.drop_constraint('proposal_space_proposal_space_id_fkey', 'proposal_space', type_='foreignkey')
    op.create_foreign_key('proposal_space_proposal_space_id_fkey',
        'proposal_space', 'proposal_space', ['parent_space_id'], ['id'], ondelete='SET NULL')


def downgrade():
    op.drop_constraint('proposal_space_proposal_space_id_fkey', 'proposal_space', type_='foreignkey')
    op.create_foreign_key('proposal_space_proposal_space_id_fkey',
        'proposal_space', 'proposal_space', ['parent_space_id'], ['id'])
