"""Miscellaneous background jobs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol, cast

import requests
from flask import g

from baseframe import statsd

from .. import app, rq
from ..extapi.boxoffice import Boxoffice
from ..extapi.explara import ExplaraAPI
from ..models import (
    EmailAddress,
    GeoName,
    PhoneNumber,
    Project,
    ProjectLocation,
    TicketClient,
    db,
)
from ..signals import emailaddress_refcount_dropping, phonenumber_refcount_dropping
from ..typing import P, ResponseType, T_co
from .helpers import app_context


class RqJobProtocol(Protocol[P, T_co]):
    """Protocol for an RQ job function."""

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T_co:
        ...

    # TODO: Replace return type with job id type
    def queue(self, *args: P.args, **kwargs: P.kwargs) -> None:
        ...

    # TODO: Add other methods and attrs (queue_name, schedule, cron, ...)


def rqjob(
    queue: str = 'funnel', **rqargs: Any
) -> Callable[[Callable[P, T_co]], RqJobProtocol[P, T_co]]:
    """Decorate an RQ job with app context."""

    def decorator(f: Callable[P, T_co]) -> RqJobProtocol[P, T_co]:
        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with app_context():
                return f(*args, **kwargs)

        return cast(RqJobProtocol, rq.job(queue, **rqargs)(wrapper))

    return decorator


@rqjob()
def import_tickets(ticket_client_id: int) -> None:
    """Import tickets from Boxoffice."""
    ticket_client = db.session.get(TicketClient, ticket_client_id)
    if ticket_client is not None:
        if ticket_client.name.lower() == 'explara':
            ticket_list = ExplaraAPI(
                access_token=ticket_client.client_access_token
            ).get_tickets(ticket_client.client_eventid)
            ticket_client.import_from_list(ticket_list)
        elif ticket_client.name.lower() == 'boxoffice':
            ticket_list = Boxoffice(
                access_token=ticket_client.client_access_token
            ).get_tickets(ticket_client.client_eventid)
            ticket_client.import_from_list(ticket_list)
        db.session.commit()


@rqjob()
def tag_locations(project_id: int) -> None:
    """Tag a project with geoname locations. This is legacy code pending a rewrite."""
    project = db.session.get(Project, project_id)
    if project is None:
        return
    if not project.location:
        return
    results = GeoName.parse_locations(
        project.location, special=["Internet", "Online"], bias=['IN', 'US']
    )
    geonames: dict[str, dict] = defaultdict(dict)
    tokens: list[dict] = []
    for item in results:
        if 'geoname' in item:
            geoname = item['geoname'].as_dict(alternate_titles=False)
            geonames[geoname['geonameid']]['geonameid'] = geoname['geonameid']
            geonames[geoname['geonameid']]['primary'] = geonames[
                geoname['geonameid']
            ].get('primary', True)
            for gtype, related in geoname.get('related', {}).items():
                if gtype in ['admin2', 'admin1', 'country', 'continent']:
                    geonames[related['geonameid']]['geonameid'] = related['geonameid']
                    geonames[related['geonameid']]['primary'] = False

            tokens.append(
                {
                    'token': item.get('token', ''),
                    'geoname': {
                        'name': geoname['name'],
                        'geonameid': geoname['geonameid'],
                    },
                }
            )
        else:
            tokens.append({'token': item.get('token', '')})

    project.parsed_location = {'tokens': tokens}

    for locdata in geonames.values():
        loc = db.session.get(ProjectLocation, (project_id, locdata['geonameid']))
        if loc is None:
            loc = ProjectLocation(project=project, geonameid=locdata['geonameid'])
            db.session.add(loc)
            db.session.flush()
        loc.primary = locdata['primary']
    for location in project.locations:
        if location.geonameid not in geonames:
            db.session.delete(location)
    db.session.commit()


# TODO: Deprecate this method and the AuthClient notification system
@rqjob()
def send_auth_client_notice(
    url: str,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    method: str = 'POST',
) -> None:
    """Send notice to AuthClient when some data changes."""
    requests.request(method, url, params=params, data=data, timeout=30)


# If an email address had a reference count drop during the request, make a note of
# its email_hash, and at the end of the request, queue a background job. The job will
# call .refcount() and if it still has zero references, it will be marked as forgotten
# by having the email column set to None.

# It is possible for an email address to have its refcount drop and rise again within
# the request, so it's imperative to wait until the end of the request before attempting
# to forget it. Ideally, this job should wait even longer, for several minutes or even
# up to a day.


@emailaddress_refcount_dropping.connect
def forget_email_in_request_teardown(sender: EmailAddress) -> None:
    if g:  # Only do this if we have an app context
        if not hasattr(g, 'forget_email_hashes'):
            g.forget_email_hashes = set()
        g.forget_email_hashes.add(sender.email_hash)


@phonenumber_refcount_dropping.connect
def forget_phone_in_request_teardown(sender: PhoneNumber) -> None:
    if g:  # Only do this if we have an app context
        if not hasattr(g, 'forget_phone_hashes'):
            g.forget_phone_hashes = set()
        g.forget_phone_hashes.add(sender.phone_hash)


@app.after_request
def forget_email_phone_in_background_job(response: ResponseType) -> ResponseType:
    if hasattr(g, 'forget_email_hashes'):
        for email_hash in g.forget_email_hashes:
            forget_email.queue(email_hash)
    if hasattr(g, 'forget_phone_hashes'):
        for phone_hash in g.forget_phone_hashes:
            forget_phone.queue(phone_hash)
    return response


@rqjob()
def forget_email(email_hash: str) -> None:
    """Remove an email address if it has no inbound references."""
    email_address = EmailAddress.get(email_hash=email_hash)
    if email_address is not None and email_address.refcount() == 0:
        app.logger.info("Forgetting email address with hash %s", email_hash)
        email_address.email = None
        db.session.commit()
        statsd.incr('email_address.forgotten')


@rqjob()
def forget_phone(phone_hash: str) -> None:
    """Remove a phone number if it has no inbound references."""
    phone_number = PhoneNumber.get(phone_hash=phone_hash)
    if phone_number is not None and phone_number.refcount() == 0:
        app.logger.info("Forgetting phone number with hash %s", phone_hash)
        phone_number.mark_forgotten()
        db.session.commit()
        statsd.incr('phone_number.forgotten')
