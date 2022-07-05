"""Templates for rendering HTTP error pages (4xx, 500)."""

from __future__ import annotations

from coaster.views import render_with

from .. import app
from ..models import db


@app.errorhandler(403)
@render_with('403.html.jinja2', json=True)
def error403(e):
    return {
        'status': 'error',
        'error': '403',
        'error_description': '403 Forbidden',
    }, 403


@app.errorhandler(404)
@render_with('404.html.jinja2', json=True)
def error404(e):
    return {
        'status': 'error',
        'error': '404',
        'error_description': '404 Not Found',
    }, 404


@app.errorhandler(405)
@render_with('405.html.jinja2', json=True)
def error405(e):
    return {
        'status': 'error',
        'error': '405',
        'error_description': '405 Method Not Allowed',
    }, 405


@app.errorhandler(410)
@render_with('410.html.jinja2', json=True)
def error410(e):
    return {
        'status': 'error',
        'error': '410',
        'error_description': '410 Gone',
    }, 410


@app.errorhandler(429)
@render_with('429.html.jinja2', json=True)
def error429(e):
    return {
        'status': 'error',
        'error': '429',
        'error_description': '429 Too Many Requests',
    }, 429


@app.errorhandler(500)
@render_with('500.html.jinja2', json=True)
def error500(e):
    db.session.rollback()
    return {
        'status': 'error',
        'error': '500',
        'error_description': '500 Internal Server Error',
    }, 500


@app.errorhandler(503)
@render_with('503.html.jinja2', json=True)
def error503(e):
    return {
        'status': 'error',
        'error': '503',
        'error_description': '503 Service Unavailable',
    }, 503
