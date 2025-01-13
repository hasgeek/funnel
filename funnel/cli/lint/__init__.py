"""Linter commands."""

from flask.cli import AppGroup

from ... import app

lint = AppGroup('lint', help="Periodic tasks from cron (with recommended intervals)")

from . import jinja

app.cli.add_command(lint)

__all__ = ['jinja', 'lint']
