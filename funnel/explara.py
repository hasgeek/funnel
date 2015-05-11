# -*- coding: utf-8 -*-

import requests

__all__ = ['ExplaraAPI']


class ExplaraAPI(object):
    # explara_api = ExplaraAPI({'access_token'}: app.config.get('EXPLARA_ACCESS_TOKEN'))
    # tickets = explara_api.get_tickets(app.config.get('EXPLARA_EVENT_IDS').get('rootconf-2015'))
    def __init__(self, config):
        self.access_token = config.get('access_token')

    def get_orders(self, explara_event_id):
        access_token = self.access_token
        headers = {'Authorization': 'Bearer {0}'.format(access_token)}
        attendee_list_url = 'https://www.explara.com/api/e/attendee-list'
        ticket_orders = []
        completed = False
        from_record = 0
        to_record = 50
        while not completed:
            payload = {'eventId': explara_event_id, 'fromRecord': from_record, 'toRecord': to_record}
            attendee_response = requests.post(attendee_list_url, headers=headers, data=payload).json()
            if not attendee_response.get('attendee'):
                completed = True
            elif isinstance(attendee_response.get('attendee'), list):
                ticket_orders.append([order for order in attendee_response.get('attendee')])
            # after the first batch, subsequent batches are dicts with batch no. as key.
            elif isinstance(attendee_response.get('attendee'), dict):
                ticket_orders.append([order for id, order in attendee_response.get('attendee').iteritems()])
            from_record = to_record
            to_record += 50

        return [order for order_list in ticket_orders for order in order_list]

    def get_tickets(self, event_id):
        orders = self.get_orders(event_id)
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
                        'phone': details.get('Phone') or order.get('phoneNo'),
                        'twitter': details.get('Twitter handle'),
                        'job_title': details.get('Job title'),
                        'company': details.get('Company name'),
                        'city': attendee.get('city'),
                        'ticket_no': attendee.get('ticketNo'),
                        'ticket_type': attendee.get('ticketName'),
                        'order_no': order.get('orderNo'),
                    })
        return tickets
