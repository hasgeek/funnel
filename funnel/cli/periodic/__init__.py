"""Periodic commands."""

from flask.cli import AppGroup

from ... import app

periodic = AppGroup(
    'periodic', help="Periodic tasks from cron (with recommended intervals)"
)

from . import mnrl, notification, stats

app.cli.add_command(periodic)

__all__ = ['periodic', 'mnrl', 'notification', 'stats']
