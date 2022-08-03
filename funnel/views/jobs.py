"""Miscellaneous background jobs."""

from __future__ import annotations

from collections import defaultdict
from functools import wraps

from flask import g

import requests

from baseframe import statsd

from .. import app, rq
from ..extapi.boxoffice import Boxoffice
from ..extapi.explara import ExplaraAPI
from ..models import EmailAddress, GeoName, Project, ProjectLocation, TicketClient, db
from ..signals import emailaddress_refcount_dropping
from ..typing import ResponseType, ReturnDecorator, WrappedFunc
from .helpers import app_context


def rqjob(queue: str = 'funnel', **rqargs) -> ReturnDecorator:
    """Decorate an RQ job with app context."""

    def decorator(f: WrappedFunc):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with app_context():
                return f(*args, **kwargs)

        return rq.job(queue, **rqargs)(wrapper)

    return decorator


@rqjob()
def import_tickets(ticket_client_id):
    """Import tickets from Boxoffice."""
    ticket_client = TicketClient.query.get(ticket_client_id)
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
def tag_locations(project_id):
    """
    Tag a project with geoname locations.

    This function used to retrieve data from Hascore, which has been merged into Funnel
    and is available directly as the GeoName model. This code continues to operate with
    the legacy Hascore data structure, and is pending rewrite.
    """
    project = Project.query.get(project_id)
    if not project.location:
        return
    results = GeoName.parse_locations(
        project.location, special=["Internet", "Online"], bias=['IN', 'US']
    )
    geonames = defaultdict(dict)
    tokens = []
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
        loc = ProjectLocation.query.get((project_id, locdata['geonameid']))
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
def send_auth_client_notice(url, params=None, data=None, method='POST'):
    """Send notice to AuthClient when some data changes."""
    requests.request(method, url, params=params, data=data)


# If an email address had a reference count drop during the request, make a note of
# its email_hash, and at the end of the request, queue a background job. The job will
# call .refcount() and if it still has zero references, it will be marked as forgotten
# by having the email column set to None.

# It is possible for an email address to have its refcount drop and rise again within
# the request, so it's imperative to wait until the end of the request before attempting
# to forget it. Ideally, this job should wait even longer, for several minutes or even
# up to a day.


@emailaddress_refcount_dropping.connect
def forget_email_in_request_teardown(sender) -> None:
    if g:  # Only do this if we have an app context
        if not hasattr(g, 'forget_email_hashes'):
            g.forget_email_hashes = set()
        g.forget_email_hashes.add(sender.email_hash)


@app.after_request
def forget_email_in_background_job(response: ResponseType) -> ResponseType:
    if hasattr(g, 'forget_email_hashes'):
        for email_hash in g.forget_email_hashes:
            forget_email.queue(email_hash)
    return response


@rqjob()
def forget_email(email_hash):
    """Remove an email address if it has no inbound references."""
    email_address = EmailAddress.get(email_hash=email_hash)
    if email_address.refcount() == 0:
        app.logger.info("Forgetting email address with hash %s", email_hash)
        email_address.email = None
        db.session.commit()
        statsd.incr('email_address.forgotten')
