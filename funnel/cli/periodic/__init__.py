"""Periodic commands."""

from flask.cli import AppGroup

from ... import app

periodic = AppGroup(
    'periodic', help="Periodic tasks from cron (with recommended intervals)"
)

from . import mnrl, notification, stats, sync

app.cli.add_command(periodic)

__all__ = ['mnrl', 'notification', 'periodic', 'stats', 'sync']
