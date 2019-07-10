"""Space content

Revision ID: 577689971aa0
Revises: 1195a2789872
Create Date: 2014-03-02 23:32:16.343014

"""

# revision identifiers, used by Alembic.
revision = '577689971aa0'
down_revision = '1195a2789872'

import sqlalchemy as sa  # NOQA
from alembic import op

from coaster.sqlalchemy import JsonDict


def upgrade():
    op.add_column('proposal_space', sa.Column('content', JsonDict, server_default='{}', nullable=False))
    op.alter_column('proposal_space', 'content', server_default=None)


def downgrade():
    op.drop_column('proposal_space', 'content')
