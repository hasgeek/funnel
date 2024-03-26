"""Periodic scans for notifications to be sent out."""

from __future__ import annotations

from datetime import timedelta

from ... import models
from ...models import db, sa, sa_orm
from ...views.notification import dispatch_notification
from . import periodic


@periodic.command('project_starting_alert')
def project_starting_alert() -> None:
    """Send alerts for sessions that are about to start (5m)."""
    # Rollback to the most recent 5 minute interval, to account for startup delay
    # for periodic job processes.
    use_now = db.session.query(
        sa.func.date_trunc('hour', sa.func.utcnow())
        + sa.cast(sa.func.date_part('minute', sa.func.utcnow()), sa.Integer)
        / 5
        * timedelta(minutes=5)
    ).scalar()

    # Find all projects that have a session starting between 10 and 15 minutes from
    # use_now, and where the same project did not have a session ending within
    # the prior hour.
    for project in (
        models.Project.starting_at(
            use_now + timedelta(minutes=10),
            timedelta(minutes=5),
            timedelta(minutes=60),
        )
        .options(sa_orm.load_only(models.Project.uuid))
        .all()
    ):
        dispatch_notification(
            models.ProjectStartingNotification(
                document=project,
                fragment=project.next_session_from(use_now + timedelta(minutes=10)),
            )
        )

    # Find all projects with a venue that have a session starting 24 hours from now
    for project in (
        models.Project.starting_at(
            use_now + timedelta(hours=24), timedelta(minutes=10), timedelta(minutes=60)
        )
        .filter(
            models.Venue.query.filter(
                models.Venue.project_id == models.Project.id
            ).exists()
        )
        .options(sa.orm.load_only(models.Project.uuid))
        .all()
    ):
        dispatch_notification(
            models.ProjectTomorrowNotification(
                document=project,
                fragment=project.next_session_from(use_now + timedelta(hours=24)),
            )
        )
