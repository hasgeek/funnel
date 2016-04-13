# -*- coding: utf-8 -*-

import requests
from ..util import extract_twitter_handle

__all__ = ['Boxoffice']


def strip_or_empty(val):
    return unicode(val).strip() if val else ''


class Boxoffice(object):
    """
    An interface that enables data retrieval from Boxoffice.
    """
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'https://boxoffice.hasgeek.com/api/1'

    def url_for(self, endpoint):
        return self.base_url.format(endpoint)

    def get_orders(self, ic):
        resp = requests.get(self.base_url + '/ic/{ic}/orders?access_token={token}'.format(ic=ic, token=self.access_token))
        return resp.json().get('orders')

    def get_tickets(self, ic):
        tickets = []
        for order in self.get_orders(ic):
            for line_item in order.get('line_items'):
                # we sometimes get an empty array for details
                if line_item.get('assignee', {}).get('email'):
                    tickets.append({
                        'fullname': strip_or_empty(line_item.get('assignee', {}).get('fullname')),
                        'email': strip_or_empty(line_item.get('assignee', {}).get('email')),
                        'phone': strip_or_empty(line_item.get('assignee', {}).get('phone')),
                        'twitter': extract_twitter_handle(strip_or_empty(line_item.get('assignee', {}).get('twitter'))),
                        'company': strip_or_empty(line_item.get('assignee', {}).get('company')),
                        'city': strip_or_empty(line_item.get('assignee', {}).get('city')),
                        'ticket_no': strip_or_empty(line_item.get('line_item_seq')),
                        'ticket_type': strip_or_empty(line_item.get('item', {}).get('title')),
                        'order_no': strip_or_empty(order.get('invoice_no')),
                    })
        return tickets
