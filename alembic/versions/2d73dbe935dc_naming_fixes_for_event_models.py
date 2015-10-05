"""naming fixes

Revision ID: 2d73dbe935dc
Revises: 380089617763
Create Date: 2015-09-30 14:12:47.074389

"""

# revision identifiers, used by Alembic.
revision = '2d73dbe935dc'
down_revision = '380089617763'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('ticket_client', 'client_event_id', new_column_name='client_eventid')
    op.alter_column('ticket_client', 'client_id', new_column_name='clientid')

    op.drop_constraint('sync_ticket_ticket_client_id', 'sync_ticket', type_='foreignkey')
    op.create_foreign_key('sync_ticket_ticket_client_id_fkey', 'sync_ticket', 'ticket_client', ['ticket_client_id'], ['id'])

    op.drop_constraint('event_proposal_space_id_name', 'event', type_='unique')
    op.create_unique_constraint('event_proposal_space_id_name_key', 'event', ['proposal_space_id', 'name'])

    op.drop_constraint(u'contact_exchange_user_id_proposal_space_id_participant_id_pk', 'contact_exchange', type_='unique')
    op.create_primary_key(u'contact_exchange_user_id_proposal_space_id_participant_id_key', 'contact_exchange', ['user_id', 'proposal_space_id', 'participant_id'])

    op.drop_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no', 'sync_ticket', type_='unique')
    op.create_unique_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no_key', 'sync_ticket', ['proposal_space_id', 'order_no', 'ticket_no'])

    op.alter_column('participant', 'email', type_=sa.Unicode(length=254))


def downgrade():
    op.alter_column('ticket_client', 'client_eventid', new_column_name='client_event_id')
    op.alter_column('ticket_client', 'clientid', new_column_name='client_id')

    op.drop_constraint('sync_ticket_ticket_client_id_fkey', 'sync_ticket', type_='foreignkey')
    op.create_foreign_key('sync_ticket_ticket_client_id', 'sync_ticket', 'ticket_client', ['ticket_client_id'], ['id'])

    op.drop_constraint('event_proposal_space_id_name_key', 'event', type_='unique')
    op.create_unique_constraint('event_proposal_space_id_name', 'event', ['proposal_space_id', 'name'])

    op.drop_constraint(u'contact_exchange_user_id_proposal_space_id_participant_id_key', 'contact_exchange', type_='unique')
    op.create_primary_key(u'contact_exchange_user_id_proposal_space_id_participant_id_pk', 'contact_exchange', ['user_id', 'proposal_space_id', 'participant_id'])

    op.drop_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no_key', 'sync_ticket', type_='unique')
    op.create_unique_constraint(u'sync_ticket_proposal_space_id_order_no_ticket_no', 'sync_ticket', ['proposal_space_id', 'order_no', 'ticket_no'])

    op.alter_column('participant', 'email', type_=sa.Unicode(length=80))
