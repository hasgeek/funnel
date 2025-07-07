"""Periodic data sync."""

from __future__ import annotations

from collections.abc import Iterable

import click

from ...models import Project
from ...views.jobs import import_tickets
from . import periodic


@periodic.command('sync')
@click.argument('projects', type=str, nargs=-1)
def sync(projects: Iterable[str]) -> None:
    """Sync tickets for specified projects (2m)."""
    if not projects:
        raise click.UsageError("Specify projects to sync as account/project.")
    for name in projects:
        project = Project.get(name)
        if project is None:
            raise click.BadParameter(f"Project {name} does not exist")
        if not project.ticket_clients:
            raise click.BadParameter(f"Project {name} has nothing to sync")
        for ticket_client in project.ticket_clients:
            import_tickets.enqueue(ticket_client.id)
