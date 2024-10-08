"""Views for shortlink app."""

from __future__ import annotations

from datetime import timedelta

from flask import abort, redirect

from coaster.utils import utcnow

from .. import app, shortlinkapp, unsubscribeapp
from ..models import Shortlink
from ..typing import Response
from .helpers import app_url_for


@shortlinkapp.route('/', endpoint='index')
def shortlink_index() -> Response:
    """Shortlink app doesn't have a page, so redirect to main app's index."""
    return redirect(app_url_for(app, 'index'), 301)


@shortlinkapp.route('/<header>/<name>')  # 'header' is required for SMS DLT URLs
@shortlinkapp.route('/<name>', defaults={'header': None})
def link(name: str, header: str | None = None) -> Response:  # noqa: ARG001
    """Redirect from a shortlink to the full link."""
    sl = Shortlink.get(name, True)
    if sl is None:
        abort(404)
    if not sl.enabled:
        abort(410)
    response = redirect(str(sl.url), 301)
    response.cache_control.private = True
    response.cache_control.max_age = 90
    response.expires = utcnow() + timedelta(seconds=90)

    # These two borrowed from Bitly and TinyURL's response headers. They tell the
    # browser to reproduce the HTTP `Referer` header that was sent to this endpoint, to
    # send it again to the destination URL

    # Needs Werkzeug >= 2.0.2
    response.content_security_policy['referrer'] = 'always'
    response.headers['Referrer-Policy'] = 'unsafe-url'
    # TODO: Perform analytics here: log client, set session cookie, etc
    return response


@unsubscribeapp.route('/', endpoint='index')
def unsubscribe_index() -> Response:
    """Redirect to SMS notification preferences."""
    return redirect(
        app_url_for(app, 'notification_preferences', utm_medium='sms', _anchor='sms'),
        301,
    )


@unsubscribeapp.route('/<token>')
def unsubscribe_short(token: str) -> Response:
    """Redirect to full length unsubscribe URL."""
    response = redirect(
        app_url_for(app, 'notification_unsubscribe_short', token=token), 301
    )
    # Set referrer as in the shortlink app
    response.content_security_policy['referrer'] = 'always'
    response.headers['Referrer-Policy'] = 'unsafe-url'
    return response
