from ..models import (db, TicketClient)
from ..extapi.explara import ExplaraAPI
from ..extapi.boxoffice import Boxoffice
from funnel import app


def import_tickets(ticket_client_id):
    with app.test_request_context():
        ticket_client = TicketClient.query.get(ticket_client_id)
        if ticket_client:
            if ticket_client.name.lower() == u'explara':
                ticket_list = ExplaraAPI(access_token=ticket_client.client_access_token).get_tickets(ticket_client.client_eventid)
                ticket_client.import_from_list(ticket_list)
            elif ticket_client.name.lower() == u'boxoffice':
                ticket_list = Boxoffice(access_token=ticket_client.client_access_token).get_tickets(ticket_client.client_eventid)
                ticket_client.import_from_list(ticket_list)
            db.session.commit()
