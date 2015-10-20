from ..models import (db, TicketClient, SyncTicket)
from ..extapi.explara import ExplaraAPI
from flask.ext.rq import job
from funnel import app


@job('talkfunnel')
def import_tickets(env, ticket_client_id):
    with app.test_request_context():
        ticket_client = TicketClient.query.get(ticket_client_id)
        if ticket_client and ticket_client.name == u'explara':
            ticket_list = ExplaraAPI(access_token=ticket_client.client_access_token).get_tickets(ticket_client.client_eventid)
            # cancelled tickets are excluded from the list returned by get_tickets
            cancel_list = SyncTicket.exclude(ticket_client, [ticket.get('ticket_no') for ticket in ticket_list]).all()
            ticket_client.import_from_list(ticket_list, cancel_list=cancel_list)

    db.session.commit()
