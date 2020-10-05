from __future__ import unicode_literals

from flask import current_app, redirect, request
from werkzeug.routing import RequestRedirect
import werkzeug.exceptions as exceptions

from coaster.views import render_with

from .. import app
from ..models import db


@app.errorhandler(exceptions.Forbidden)
@render_with('403.html.jinja2', json=True)
def error403(e):
    return {'error': "403 Forbidden"}, 403


@app.errorhandler(exceptions.NotFound)
@render_with('404.html.jinja2', json=True)
def error404(e):
    if request.path.endswith('/') and request.method == 'GET':
        newpath = request.path[:-1]
        try:
            adapter = current_app.url_map.bind_to_environ(request)
            matchinfo = adapter.match(newpath)
            if matchinfo[0] != request.endpoint:
                # Redirect only if it's not back to the same endpoint
                redirect_url = request.base_url[:-1]
                if request.query_string:
                    redirect_url = (
                        redirect_url + '?' + request.query_string.decode('utf-8')
                    )
                return redirect(redirect_url)
        except (exceptions.NotFound, RequestRedirect, exceptions.MethodNotAllowed):
            pass
    return {'error': "404 Not Found"}, 404


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
