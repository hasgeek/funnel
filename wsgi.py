"""WSGI apps."""

import os.path
import sys

from flask.cli import load_dotenv
from flask.helpers import get_load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

__all__ = ['application', 'shortlinkapp', 'unsubscribeapp']

sys.path.insert(0, os.path.dirname(__file__))
if get_load_dotenv():
    load_dotenv()

# pylint: disable=wrong-import-position
from funnel import app as application, shortlinkapp, unsubscribeapp  # isort:skip

application.wsgi_app = ProxyFix(application.wsgi_app)  # type: ignore[method-assign]
shortlinkapp.wsgi_app = ProxyFix(shortlinkapp.wsgi_app)  # type: ignore[method-assign]
unsubscribeapp.wsgi_app = ProxyFix(  # type: ignore[method-assign]
    unsubscribeapp.wsgi_app
)
