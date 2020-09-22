from __future__ import unicode_literals

from flask import current_app, redirect, request
from werkzeug import exceptions
from werkzeug.routing import MethodNotAllowed, NotFound, RequestRedirect

from coaster.views import render_with

from .. import app
from . import baseframe_translations


@app.errorhandler(exceptions.TooManyRequests)
@render_with('429.html.jinja2', json=True)
def error429(e):
    baseframe_translations.as_default()
    return {'error': "429 Too Many Requests"}, 429


@app.errorhandler(exceptions.Gone)
@render_with('410.html.jinja2', json=True)
def error410(e):
    baseframe_translations.as_default()
    return {'error': "410 Page now gone"}, 410


@app.errorhandler(exceptions.MethodNotAllowed)
@render_with('405.html.jinja2', json=True)
def error405(e):
    baseframe_translations.as_default()
    return {'error': "405 Method Not Allowed"}, 405


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
        except (NotFound, RequestRedirect, MethodNotAllowed):
            pass
    baseframe_translations.as_default()
    return {'error': "404 Not Found"}, 404


@app.errorhandler(exceptions.Forbidden)
@render_with('403.html.jinja2', json=True)
def error403(e):
    baseframe_translations.as_default()
    return {'error': "403 Forbidden"}, 403


@app.errorhandler(exceptions.InternalServerError)
@render_with('500.html.jinja2', json=True)
def error500(e):
    if current_app.extensions and 'sqlalchemy' in current_app.extensions:
        current_app.extensions['sqlalchemy'].db.session.rollback()

    baseframe_translations.as_default()
    return {'error': "500 Internal Server Error"}, 500


@app.errorhandler(exceptions.ServiceUnavailable)
@render_with('503.html.jinja2', json=True)
def error503(e):
    baseframe_translations.as_default()
    return {'error': "503 Service Unavailable"}, 503
