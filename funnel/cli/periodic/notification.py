"""Periodic scans for notifications to be sent out."""

from __future__ import annotations

from datetime import timedelta

from ... import models
from ...models import db, sa
from ...views.notification import dispatch_notification
from . import periodic


@periodic.command('project_starting_alert')
def project_starting_alert() -> None:
    """Send notifications for projects that are about to start schedule (5m)."""
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

    # Any eager-loading columns and relationships should be deferred with
    # sa.orm.defer(column) and sa.orm.noload(relationship). There are none as of this
    # commit.
    for project in (
        models.Project.starting_at(
            use_now + timedelta(minutes=10),
            timedelta(minutes=5),
            timedelta(minutes=60),
        )
        .options(sa.orm.load_only(models.Project.uuid))
        .all()
    ):
        dispatch_notification(
            models.ProjectStartingNotification(
                document=project,
                fragment=project.next_session_from(use_now + timedelta(minutes=10)),
            )
        )
