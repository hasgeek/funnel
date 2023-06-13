"""Periodic commands."""

from flask.cli import AppGroup

from ... import app

periodic = AppGroup(
    'periodic', help="Periodic tasks from cron (with recommended intervals)"
)

from . import stats  # isort:skip  # noqa: F401
from . import notification  # isort:skip  # noqa: F401

app.cli.add_command(periodic)
