"""Event timezone

Revision ID: 55097480a655
Revises: 3a6b2ab00e3e
Create Date: 2013-11-09 15:53:48.318340

"""

# revision identifiers, used by Alembic.
revision = '55097480a655'
down_revision = '3a6b2ab00e3e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('proposal_space', sa.Column('timezone', sa.Unicode(length=40), nullable=False, server_default=u'UTC'))
    op.alter_column('proposal_space', 'timezone', server_default=None)


def downgrade():
    op.drop_column('proposal_space', 'timezone')
