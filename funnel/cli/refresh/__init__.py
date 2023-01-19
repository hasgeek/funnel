"""Refresh commands."""
from flask.cli import AppGroup

from ... import app

refresh = AppGroup('refresh', help="Refresh or purge caches")

from . import markdown  # isort:skip  # noqa: F401

app.cli.add_command(refresh)
