from __future__ import unicode_literals

import werkzeug.exceptions as exceptions

from coaster.views import render_with

from .. import app
from ..models import db


@app.errorhandler(exceptions.Forbidden)
@render_with('403.html.jinja2', json=True)
def error403(e):
    return {'error': "403 Forbidden"}, 403


@app.errorhandler(exceptions.MethodNotAllowed)
@render_with('405.html.jinja2', json=True)
def error405(e):
    return {'error': "405 Method Not Allowed"}, 405


@app.errorhandler(exceptions.Gone)
@render_with('410.html.jinja2', json=True)
def error410(e):
    return {'error': "410 Gone"}, 410


@app.errorhandler(exceptions.TooManyRequests)
@render_with('429.html.jinja2', json=True)
def error429(e):
    return {'error': "429 Too Many Requests"}, 429


@app.errorhandler(exceptions.InternalServerError)
@render_with('500.html.jinja2', json=True)
def error500(e):
    db.session.rollback()
    return {'error': "500 Internal Server Error"}, 500


@app.errorhandler(exceptions.ServiceUnavailable)
@render_with('503.html.jinja2', json=True)
def error503(e):
    return {'error': "503 Service Unavailable"}, 503
