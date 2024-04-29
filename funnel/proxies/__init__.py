"""Proxies for run-time access."""

from flask import Flask

from .request import RequestWants, request_wants, response_varies

__all__ = ['RequestWants', 'request_wants']


def init_app(app: Flask) -> None:
    """Make proxies available in Jinja templates."""
    app.jinja_env.globals['request_wants'] = request_wants
    app.after_request(response_varies)
