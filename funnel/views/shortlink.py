from __future__ import annotations

from datetime import datetime, timedelta

from flask import abort, redirect

from .. import app, shortlinkapp
from ..models import Shortlink
from .helpers import app_url_for


@shortlinkapp.route('/')
def index():
    return redirect(app_url_for(app, 'index'), code=301)


@shortlinkapp.route('/<name>')
def link(name):
    sl = Shortlink.get(name, True)
    if sl is None:
        abort(404)
    if not sl.enabled:
        abort(410)
    response = redirect(str(sl.url), 301)
    response.cache_control.private = True
    response.cache_control.max_age = 90
    response.expires = datetime.utcnow() + timedelta(seconds=90)
    # These two borrowed from Bitly and TinyURL's response headers. They tell the
    # browser to reproduce the HTTP Referer header that was sent to this endpoint, to
    # send it again to the destination URL
    response.content_security_policy['referrer'] = 'always'  # Needs Werkzeug >= 2.0.2
    response.headers['Referrer-Policy'] = 'unsafe-url'
    # TODO: Perform analytics here: log client, set session cookie, etc
    return response
