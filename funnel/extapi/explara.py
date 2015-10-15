# -*- coding: utf-8 -*-

import requests
from ..util import format_twitter
from ..models import SyncTicket

__all__ = ['ExplaraAPI']


class ExplaraAPI(object):
    """
    An interface that enables data retrieval from Explara.
    Reference : https://developers.explara.com/api-document
    """
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {'Authorization': u'Bearer ' + self.access_token}
        self.base_url = 'https://www.explara.com/api/e/{0}'

    def url_for(self, endpoint):
        return self.base_url.format(endpoint)

    def get_orders(self, explara_eventid):
        """
        Gets the entire dump of orders for a given eventid in batches of 50,
        owing to the restriction imposed by Explara's API.
        Explara does not make any assurances w.r.t the order; hence no order is assumed and
        the entire dump is retrieved.
        """
        ticket_orders = []
        completed = False
        from_record = 0
        to_record = 50
        while not completed:
            payload = {'eventId': explara_eventid, 'fromRecord': from_record, 'toRecord': to_record}
            attendee_response = requests.post(self.url_for('attendee-list'), headers=self.headers, data=payload).json()
            if not attendee_response.get('attendee'):
                completed = True
            elif isinstance(attendee_response.get('attendee'), list):
                ticket_orders.extend(attendee_response['attendee'])
            # after the first batch, subsequent batches are dicts with batch no. as key.
            elif isinstance(attendee_response.get('attendee'), dict):
                ticket_orders.extend(attendee_response['attendee'].values())
            from_record = to_record
            to_record += 50

        return ticket_orders

    def get_tickets(self, explara_eventid):
        tickets = []
        for order in self.get_orders(explara_eventid):
            for attendee in order.get('attendee'):
                # cancelled tickets are in this list too, hence the check
                if attendee.get('status') == 'attending':
                    # we sometimes get an empty array for details
                    details = attendee.get('details') or {}
                    tickets.append({
                        'fullname': attendee.get('name'),
                        'email': attendee.get('email'),
                        'phone': details.get('Phone') or order.get('phoneNo', ''),
                        'twitter': format_twitter(details.get('Twitter handle', '')),
                        'job_title': details.get('Job title', ''),
                        'company': details.get('Company name', ''),
                        'city': order.get('city', ''),
                        'ticket_no': attendee.get('ticketNo'),
                        'ticket_type': attendee.get('ticketName').strip(),
                        'order_no': order.get('orderNo'),
                    })
        return tickets

    def import_tickets(self, space, ticket_client):
        ticket_list = self.get_tickets(ticket_client.client_eventid)
        # cancelled tickets are excluded from the list returned by get_tickets
        cancel_list = SyncTicket.exclude(space, ticket_client, [ticket.get('ticket_no') for ticket in ticket_list]).all()
        ticket_client.import_from_list(space, ticket_list, cancel_list=cancel_list)
