# -*- coding: utf-8 -*-

import requests
from ..util import extract_twitter_handle
from .. import app

__all__ = ['Boxoffice']


class Boxoffice(object):
    """
    An interface that enables data retrieval from Boxoffice.
    """
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = app.config['BOXOFFICE_SERVER']

    def url_for(self, endpoint):
        return self.base_url.format(endpoint)

    def get_orders(self, ic):
        resp = requests.get(self.base_url + '/ic/{ic}/orders?access_token={token}'.format(ic=ic, token=self.access_token))
        return resp.json().get('orders')

    def get_tickets(self, ic):
        tickets = []
        for order in self.get_orders(ic):
            for line_item in order.get('line_items'):
                if line_item.get('assignee'):
                    if line_item.get('line_item_status') == u'confirmed':
                        status = u'confirmed'
                    elif line_item.get('line_item_status') == u'cancelled':
                        status = u'cancelled'
                    else:
                        status = unicode(line_item.get('line_item_status'))
                    tickets.append({
                        'fullname': line_item.get('assignee').get('fullname', ''),
                        'email': line_item.get('assignee').get('email'),
                        'phone': line_item.get('assignee').get('phone', ''),
                        'twitter': extract_twitter_handle(line_item.get('assignee').get('twitter', '')),
                        'company': line_item.get('assignee').get('company'),
                        'city': line_item.get('assignee').get('city', ''),
                        'job_title': line_item.get('assignee').get('jobtitle', ''),
                        'ticket_no': unicode(line_item.get('line_item_seq')),
                        'ticket_type': line_item.get('item', {}).get('title', '')[:80],
                        'order_no': unicode(order.get('invoice_no')),
                        'status': status
                        })

        return tickets
