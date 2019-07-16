# -*- coding: utf-8 -*-

"""remove proposal_space_id from sync_ticket

Revision ID: 2d55f804a4ed
Revises: 48ce908329c0
Create Date: 2015-10-15 18:33:31.847676

"""

# revision identifiers, used by Alembic.
revision = '2d55f804a4ed'
down_revision = '48ce908329c0'

import sqlalchemy as sa  # NOQA
from alembic import op
from sqlalchemy.sql import column, select, table


def upgrade():
    op.drop_constraint(
        'sync_ticket_proposal_space_id_order_no_ticket_no_key',
        'sync_ticket',
        type_='unique',
    )
    op.create_unique_constraint(
        'sync_ticket_ticket_client_id_order_no_ticket_no_key',
        'sync_ticket',
        ['ticket_client_id', 'order_no', 'ticket_no'],
    )
    op.drop_constraint(
        'sync_ticket_proposal_space_id_fkey', 'sync_ticket', type_='foreignkey'
    )
    op.drop_column('sync_ticket', 'proposal_space_id')


def downgrade():
    op.add_column(
        'sync_ticket',
        sa.Column(
            'proposal_space_id', sa.INTEGER(), autoincrement=False, nullable=True
        ),
    )
    op.create_foreign_key(
        'sync_ticket_proposal_space_id_fkey',
        'sync_ticket',
        'proposal_space',
        ['proposal_space_id'],
        ['id'],
    )
    op.drop_constraint(
        'sync_ticket_ticket_client_id_order_no_ticket_no_key',
        'sync_ticket',
        type_='unique',
    )
    op.create_unique_constraint(
        'sync_ticket_proposal_space_id_order_no_ticket_no_key',
        'sync_ticket',
        ['proposal_space_id', 'order_no', 'ticket_no'],
    )
    # restore proposal_space_ids
    sync_ticket = table(
        'sync_ticket', column('proposal_space_id'), column('ticket_client_id')
    )
    ticket_client = table('ticket_client', column('id'), column('proposal_space_id'))
    op.execute(
        sync_ticket.update().values(
            {
                'proposal_space_id': select([ticket_client.c.proposal_space_id]).where(
                    ticket_client.c.id == sync_ticket.c.ticket_client_id
                )
            }
        )
    )
