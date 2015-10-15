"""remove proposal_space_id from sync_ticket

Revision ID: 2d55f804a4ed
Revises: 48ce908329c0
Create Date: 2015-10-15 18:33:31.847676

"""

# revision identifiers, used by Alembic.
revision = '2d55f804a4ed'
down_revision = '48ce908329c0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no_key', 'sync_ticket', type_='unique')
    op.create_unique_constraint(u'sync_ticket_ticket_client_id_order_no_ticket_no_key', 'sync_ticket', ['ticket_client_id', 'order_no', 'ticket_no'])
    op.drop_constraint(u'sync_ticket_proposal_space_id_fkey', 'sync_ticket', type_='foreignkey')
    op.drop_column('sync_ticket', 'proposal_space_id')


def downgrade():
    op.add_column('sync_ticket', sa.Column('proposal_space_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key(u'sync_ticket_proposal_space_id_fkey', 'sync_ticket', 'proposal_space', ['proposal_space_id'], ['id'])
    op.drop_constraint(u'sync_ticket_ticket_client_id_order_no_ticket_no_key', 'sync_ticket', type_='unique')
    op.create_unique_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no_key', 'sync_ticket', ['proposal_space_id', 'order_no', 'ticket_no'])
