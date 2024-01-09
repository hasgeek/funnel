"""External API support for Explara."""

from __future__ import annotations

from typing import Any, TypedDict, cast

import requests

from ..utils import extract_twitter_handle
from .typing import ExtTicketsDict

__all__ = ['ExplaraAPI']


def strip_or_empty(val: Any) -> str:
    return val.strip() if isinstance(val, str) else ''


class ExplaraAttendeeDict(TypedDict, total=False):
    name: str
    email: str
    Phone: str
    phoneNo: str  # noqa: N815
    ticketNo: str  # noqa: N815
    ticketName: str  # noqa: N815
    orderNo: str  # noqa: N815
    status: str


class ExplaraOrderDict(TypedDict):
    attendee: list[ExplaraAttendeeDict]


class ExplaraAPI:
    """
    Interface that enables data retrieval from Explara.

    Reference : https://developers.explara.com/api-document
    """

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self.headers = {'Authorization': 'Bearer ' + self.access_token}
        self.base_url = 'https://www.explara.com/api/e/{0}'

    def url_for(self, endpoint: str) -> str:
        return self.base_url.format(endpoint)

    def get_orders(self, explara_eventid: str) -> list[ExplaraOrderDict]:
        """
        Get the entire dump of orders for a given eventid in batches.

        Batches are of size 50, owing to the restriction imposed by Explara's API.
        Explara does not make any assurances w.r.t the order; hence no order is assumed
        and the entire dump is retrieved.
        """
        ticket_orders = []
        completed = False
        from_record = 0
        to_record = 50
        while not completed:
            payload = {
                'eventId': explara_eventid,
                'fromRecord': from_record,
                'toRecord': to_record,
            }
            attendee_response = requests.post(
                self.url_for('attendee-list'),
                timeout=30,
                headers=self.headers,
                data=payload,
            ).json()
            if not attendee_response.get('attendee'):
                completed = True
            elif isinstance(attendee_response.get('attendee'), list):
                ticket_orders.extend(attendee_response['attendee'])
            # after the first batch, subsequent batches are dicts with batch no. as key.
            elif isinstance(attendee_response.get('attendee'), dict):
                ticket_orders.extend(list(attendee_response['attendee'].values()))
            from_record = to_record
            to_record += 50

        return ticket_orders

    def get_tickets(self, explara_eventid: str) -> list[ExtTicketsDict]:
        tickets: list[ExtTicketsDict] = []
        for order in self.get_orders(explara_eventid):
            for attendee in order['attendee']:
                # cancelled tickets are in this list too, hence the check
                if attendee.get('status') == 'attending':
                    status: str | None = 'confirmed'
                elif attendee.get('status') in ['cancelled', 'lcancelled']:
                    status = 'cancelled'
                else:
                    status = attendee.get('status')
                # we sometimes get an empty array for details
                details = cast(dict, attendee.get('details') or {})
                tickets.append(
                    {
                        'fullname': strip_or_empty(attendee.get('name')),
                        'email': strip_or_empty(attendee.get('email')),
                        'phone': strip_or_empty(
                            details.get('Phone') or order.get('phoneNo')
                        ),
                        'twitter': extract_twitter_handle(
                            strip_or_empty(details.get('Twitter handle'))
                        ),
                        'job_title': strip_or_empty(details.get('Job title')),
                        'company': strip_or_empty(details.get('Company name')),
                        'city': strip_or_empty(order.get('city')),
                        'ticket_no': strip_or_empty(attendee.get('ticketNo')),
                        'ticket_type': strip_or_empty(attendee.get('ticketName')),
                        'order_no': strip_or_empty(order.get('orderNo')),
                        'status': status,
                    }
                )
        return tickets
