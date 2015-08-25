# -*- coding: utf-8 -*-

import requests
from ..util import format_twitter
import datetime

__all__ = ['ExplaraAPI']


class ExplaraAPI(object):
    """
    Example Use:
    ea = ExplaraAPI(access_token="xxx")
    tickets = ea.get_tickets(eventid="exxxx")
    """
    def __init__(self, access_token):
        self.access_token = access_token

    def get_events(self):
        events_url = 'https://www.explara.com/api/e/get-all-events'
        headers = {'Authorization': u'Bearer ' + self.access_token}
        events = requests.post(events_url, headers=headers).json()
        return [{'title': e.get('eventTitle'), 'eventId': e.get('eventId')} for e in events.get('events')]

    def format_order(self, order):
        """ Returns a native representation of the order """
        def date_from_string(datestr):
            return datetime.strptime(datestr.split()[0], '%Y-%m-%d')

        return {
            'order_no': order.get('orderNo'),
            'phone': order.get('phoneNo'),
            'datetime': date_from_string(order.get('purchaseDate').get('date')),
            'buyer_email': order.get('email'),
            'buyer_phone': order.get('phoneNo'),
            'paid_amount': order.get('orderCost'),
            'refund_amount': order.get('refundAmount')
        }

    def get_orders(self, explara_eventid):
        headers = {'Authorization': u'Bearer ' + self.access_token}
        attendee_list_url = 'https://www.explara.com/api/e/attendee-list'
        ticket_orders = []
        completed = False
        from_record = 0
        to_record = 50
        while not completed:
            payload = {'eventId': explara_eventid, 'fromRecord': from_record, 'toRecord': to_record}
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

    def get_tickets(self, explara_eventid):
        orders = self.get_orders(explara_eventid)
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
