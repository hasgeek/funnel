from ..models import (db, TicketClient)
from ..extapi.explara import ExplaraAPI
from flask.ext.rq import job


@job('default')
def import_tickets(env, ticket_client_id):
    from funnel import init_for
    init_for(env)
    ticket_client = TicketClient.query.get(ticket_client_id)
    if ticket_client.name == u'explara':
        ExplaraAPI(access_token=ticket_client.client_access_token).import_tickets(ticket_client)
    db.session.commit()
