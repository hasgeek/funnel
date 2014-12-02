"""Remove ProposalSpace.content

Revision ID: 436114dffa00
Revises: f8204bcd438
Create Date: 2014-12-03 02:12:33.737669

"""

# revision identifiers, used by Alembic.
revision = '436114dffa00'
down_revision = 'f8204bcd438'

from alembic import op
import sqlalchemy as sa
from coaster.sqlalchemy import JsonDict


def upgrade():
    op.drop_column('proposal_space', 'content')


def downgrade():
    op.add_column('proposal_space', sa.Column('content', JsonDict, server_default='{}', nullable=False))
    op.alter_column('proposal_space', 'content', server_default=None)
