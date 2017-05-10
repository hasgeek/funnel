# -*- coding: utf-8 -*-

import requests
from ..util import extract_twitter_handle

__all__ = ['ExplaraAPI']


def strip_or_empty(val):
    return val.strip() if val else ''


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
                    status = u'confirmed'
                elif attendee.get('status') in [u'cancelled', u'lcancelled']:
                    status = u'cancelled'
                else:
                    status = unicode(attendee.get('status'))
                # we sometimes get an empty array for details
                details = attendee.get('details') or {}
                tickets.append({
                    'fullname': strip_or_empty(attendee.get('name')),
                    'email': strip_or_empty(attendee.get('email')),
                    'phone': strip_or_empty(details.get('Phone') or order.get('phoneNo')),
                    'twitter': extract_twitter_handle(strip_or_empty(details.get('Twitter handle'))),
                    'job_title': strip_or_empty(details.get('Job title')),
                    'company': strip_or_empty(details.get('Company name')),
                    'city': strip_or_empty(order.get('city')),
                    'ticket_no': strip_or_empty(attendee.get('ticketNo')),
                    'ticket_type': strip_or_empty(attendee.get('ticketName')),
                    'order_no': strip_or_empty(order.get('orderNo')),
                    'status': status
                })
        return tickets
