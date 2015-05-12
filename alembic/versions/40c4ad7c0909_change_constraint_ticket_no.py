"""change_constraint_ticket_no

Revision ID: 40c4ad7c0909
Revises: 2c64e60b80a
Create Date: 2015-05-12 10:03:43.685909

"""

revision = '40c4ad7c0909'
down_revision = '2c64e60b80a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_constraint(u'sync_ticket_proposal_space_id_ticket_no_key', 'sync_ticket', type_='unique')
    op.create_unique_constraint(None, 'sync_ticket', ['proposal_space_id', 'order_no', 'ticket_no'])


def downgrade():
    op.drop_constraint(None, 'sync_ticket', type_='unique')
    op.create_unique_constraint(u'sync_ticket_proposal_space_id_ticket_no_key', 'sync_ticket', ['proposal_space_id', 'ticket_no'])
