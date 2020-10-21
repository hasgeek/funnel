"""Make session:proposal 1:1.

Revision ID: 3a6b2ab00e3e
Revises: 4dbf686f4380
Create Date: 2013-11-09 13:51:58.343243

"""

# revision identifiers, used by Alembic.
revision = '3a6b2ab00e3e'
down_revision = '4dbf686f4380'

from alembic import op


def upgrade():
    op.create_unique_constraint('session_proposal_id_key', 'session', ['proposal_id'])


def downgrade():
    op.drop_constraint('session_proposal_id_key', 'session', 'unique')
