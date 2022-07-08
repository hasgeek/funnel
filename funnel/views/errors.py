"""Templates for rendering HTTP error pages (4xx, 500)."""

from __future__ import annotations

from flask import current_app, json, redirect, render_template, request
from werkzeug.exceptions import HTTPException, MethodNotAllowed, NotFound
from werkzeug.routing import RequestRedirect

from .. import app
from ..models import db
from ..proxies import request_wants
from ..typing import ReturnView

templates = {
    403: '403.html.jinja2',
    404: '404.html.jinja2',
    405: '405.html.jinja2',
    410: '410.html.jinja2',
    429: '429.html.jinja2',
    500: '500.html.jinja2',
    503: '503.html.jinja2',
}


@app.errorhandler(HTTPException)
def handle_error(exc: HTTPException) -> ReturnView:
    """Render all errors with a custom template."""
    db.session.rollback()
    json_response = request_wants.json or request.path.startswith('/api/')
    response = exc.get_response()
    if json_response:
        response.data = json.dumps(
            {
                'status': 'error',
                'code': exc.code,
                'name': exc.name,
                'error': str(exc.code),
                'error_description': exc.description,
            }
        )
        response.content_type = 'application/json'
    elif exc.code in templates:
        response.data = render_template(templates[exc.code])
    return response


@app.errorhandler(404)
def handle_error404(exc: NotFound) -> ReturnView:
    """Render 404 error."""
    if exc.code == 404 and request.path.endswith('/'):
        # If the URL has a trailing slash, check if there's an endpoint handler that
        # works without the slash.
        try:
            adapter = current_app.url_map.bind_to_environ(request)
            matchinfo = adapter.match(request.path[:-1])  # Without trailing slash
            if matchinfo[0] != request.endpoint:
                # Redirect only if it's not back to the same endpoint
                redirect_url = request.base_url[:-1]
                if request.query_string:
                    redirect_url = redirect_url + '?' + request.query_string.decode()
                return redirect(redirect_url, 308)
        except (NotFound, RequestRedirect, MethodNotAllowed):
            # RequestRedirect: `adapter.match` is suggesting we try again by adding the
            # trailing slash, which obviously doesn't work
            pass

    return handle_error(exc)
