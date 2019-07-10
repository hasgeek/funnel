"""Scoped id for proposals

Revision ID: 18052b0cd282
Revises: 140c9b68d65b
Create Date: 2014-04-18 12:43:12.100890

"""

# revision identifiers, used by Alembic.
revision = '18052b0cd282'
down_revision = '140c9b68d65b'

import sqlalchemy as sa  # NOQA
from alembic import op
from sqlalchemy.sql import column, table


def upgrade():
    proposal_space = table('proposal_space',
        column('name', sa.Unicode(250)),
        column('legacy_name', sa.Unicode(250)))

    proposal = table('proposal',
        column('id', sa.Integer),
        column('url_id', sa.Integer))

    op.add_column('proposal_space', sa.Column('legacy_name', sa.Unicode(250), nullable=True))
    op.execute(proposal_space.update().values({'legacy_name': proposal_space.c.name}))
    op.create_unique_constraint('proposal_space_legacy_name_key', 'proposal_space', ['legacy_name'])

    op.add_column('proposal', sa.Column('url_id', sa.Integer(), nullable=True))
    op.execute(proposal.update().values({'url_id': proposal.c.id}))
    op.alter_column('proposal', 'url_id', nullable=False)
    op.create_unique_constraint('proposal_proposal_space_id_url_id_key', 'proposal', ['proposal_space_id', 'url_id'])


def downgrade():
    op.drop_constraint('proposal_proposal_space_id_url_id_key', 'proposal')
    op.drop_column('proposal', 'url_id')
    op.drop_constraint('proposal_space_legacy_name_key', 'proposal_space')
    op.drop_column('proposal_space', 'legacy_name')
