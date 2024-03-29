"""External API support for Boxoffice."""

from __future__ import annotations

from urllib.parse import urljoin

import requests
from flask import current_app

from ..utils import extract_twitter_handle
from .typing import ExtTicketsDict

__all__ = ['Boxoffice']


class Boxoffice:
    """Interface that enables data retrieval from Boxoffice."""

    def __init__(self, access_token: str, base_url: str | None = None) -> None:
        self.access_token = access_token
        if not base_url:
            self.base_url = current_app.config['BOXOFFICE_SERVER']
        else:
            self.base_url = base_url

    def get_orders(self, ic: str):  # TODO: Return type annotation
        url = urljoin(
            self.base_url,
            f'ic/{ic}/orders?access_token={self.access_token}',
        )
        return requests.get(url, timeout=30).json().get('orders')

    def get_tickets(self, ic: str) -> list[ExtTicketsDict]:
        tickets: list[ExtTicketsDict] = []
        for order in self.get_orders(ic):
            for line_item in order.get('line_items'):
                if line_item.get('assignee'):
                    status = line_item.get('line_item_status')
                    tickets.append(
                        {
                            'fullname': line_item.get('assignee').get('fullname', ''),
                            'email': line_item.get('assignee').get('email'),
                            'phone': line_item.get('assignee').get('phone', ''),
                            'twitter': extract_twitter_handle(
                                line_item.get('assignee').get('twitter', '')
                            ),
                            'company': line_item.get('assignee').get('company'),
                            'city': line_item.get('assignee').get('city', ''),
                            'job_title': line_item.get('assignee').get('jobtitle', ''),
                            'ticket_no': str(line_item.get('line_item_seq')),
                            'ticket_type': line_item.get('ticket', {}).get('title', '')[
                                :80
                            ],
                            'order_no': str(order.get('invoice_no')),
                            'status': status,
                        }
                    )

        return tickets
