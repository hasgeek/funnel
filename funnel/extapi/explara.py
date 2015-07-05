# -*- coding: utf-8 -*-

import requests
from ..util import format_twitter

__all__ = ['ExplaraAPI']


class ExplaraAPI(object):
    # ea = ExplaraAPI(access_token=proposal_space.client_access_token, event_id=proposal_space.client_event_id)
    # tickets = ea.get_tickets()
    def __init__(self, access_token, eventid):
        self.access_token = access_token
        self.eventid = eventid

    def get_orders(self):
        headers = {'Authorization': u'Bearer ' + self.access_token}
        attendee_list_url = 'https://www.explara.com/api/e/attendee-list'
        ticket_orders = []
        completed = False
        from_record = 0
        to_record = 50
        while not completed:
            payload = {'eventId': self.eventid, 'fromRecord': from_record, 'toRecord': to_record}
            attendee_response = requests.post(attendee_list_url, headers=headers, data=payload).json()
            if not attendee_response.get('attendee'):
                completed = True
            elif isinstance(attendee_response.get('attendee'), list):
                ticket_orders.extend([order for order in attendee_response.get('attendee')])
            # after the first batch, subsequent batches are dicts with batch no. as key.
            elif isinstance(attendee_response.get('attendee'), dict):
                ticket_orders.extend([order for order_idx, order in attendee_response.get('attendee').items()])
            from_record = to_record
            to_record += 50

        return ticket_orders

    def get_tickets(self):
        orders = self.get_orders()
        tickets = []

        for order in orders:
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
                        'city': attendee.get('city', ''),
                        'ticket_no': attendee.get('ticketNo'),
                        'ticket_type': attendee.get('ticketName'),
                        'order_no': order.get('orderNo'),
                    })
        return tickets
