"""add order ref to ticket

Revision ID: 4f8a73477649
Revises: 1217f51e4e41
Create Date: 2015-08-25 20:32:37.101861

"""

# revision identifiers, used by Alembic.
revision = '4f8a73477649'
down_revision = '1217f51e4e41'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_foreign_key('sync_ticket_order', 'sync_ticket', 'ticket_order', ['proposal_space_id', 'order_no'], ['proposal_space_id', 'order_no'])


def downgrade():
    op.drop_constraint('sync_ticket_order', 'sync_ticket', type_='foreignkey')
