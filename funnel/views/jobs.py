from collections import defaultdict

import requests

from baseframe import statsd

from .. import app, rq
from ..extapi.boxoffice import Boxoffice
from ..extapi.explara import ExplaraAPI
from ..models import EmailAddress, GeoName, Project, ProjectLocation, TicketClient, db


@rq.job('funnel')
def import_tickets(ticket_client_id):
    """Import tickets from Boxoffice."""
    with app.app_context():
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


@rq.job('funnel')
def tag_locations(project_id):
    """
    Tag a project with geoname locations.

    This function used to retrieve data from Hascore, which has been merged into Funnel
    and is available directly as the GeoName model. This code continues to operate with
    the legacy Hascore data structure, and is pending rewrite.
    """
    with app.test_request_context():
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
                        geonames[related['geonameid']]['geonameid'] = related[
                            'geonameid'
                        ]
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
@rq.job('funnel')
def send_auth_client_notice(url, params=None, data=None, method='POST'):
    """Send notice to AuthClient when some data changes."""
    requests.request(method, url, params=params, data=data)


@rq.job('funnel')
def forget_email(email_hash):
    """Remove an email address if it has no inbound references."""
    with app.app_context():
        email_address = EmailAddress.get(email_hash=email_hash)
        if email_address.refcount() == 0:
            app.logger.info("Forgetting email address with hash %s", email_hash)
            email_address.email = None
            db.session.commit()
            statsd.incr('email_address.forgotten')
