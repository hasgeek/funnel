"""Refresh commands."""

from flask.cli import AppGroup

from ... import app

refresh = AppGroup('refresh', help="Refresh or purge caches")

from . import markdown

app.cli.add_command(refresh)

__all__ = ['markdown', 'refresh']
