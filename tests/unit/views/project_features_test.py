"""Tests for project feature flags."""

from datetime import timedelta

import pytest

from coaster.utils import utcnow

from funnel import models

from ...conftest import scoped_session


@pytest.fixture
def session_yesterday(
    db_session: scoped_session, project_expo2010: models.Project
) -> models.Session:
    """Session that was yesterday."""
    now = utcnow()
    sess = models.Session(
        project=project_expo2010,
        start_at=now - timedelta(hours=24),
        end_at=now - timedelta(hours=23),
        title="Yesterday's session",
    )
    db_session.add(sess)
    db_session.commit()
    project_expo2010.update_schedule_timestamps()
    return sess


@pytest.fixture
def session_now(
    db_session: scoped_session, project_expo2010: models.Project
) -> models.Session:
    """Session that's currently underway."""
    now = utcnow()
    sess = models.Session(
        project=project_expo2010,
        start_at=now - timedelta(hours=1),
        end_at=now + timedelta(hours=1),
        title="Current session",
    )
    db_session.add(sess)
    db_session.commit()
    project_expo2010.update_schedule_timestamps()
    return sess


@pytest.fixture
def session_tomorrow(
    db_session: scoped_session, project_expo2010: models.Project
) -> models.Session:
    """Session that's almost a day away."""
    now = utcnow()
    sess = models.Session(
        project=project_expo2010,
        start_at=now + timedelta(hours=23),
        end_at=now + timedelta(hours=24),
        title="Tomorrow's session",
    )
    db_session.add(sess)
    db_session.commit()
    project_expo2010.update_schedule_timestamps()
    return sess


@pytest.fixture
def session_later(
    db_session: scoped_session, project_expo2010: models.Project
) -> models.Session:
    """Session that's more than a day away."""
    now = utcnow()
    sess = models.Session(
        project=project_expo2010,
        start_at=now + timedelta(hours=25),
        end_at=now + timedelta(hours=26),
        title="Later session",
    )
    db_session.add(sess)
    db_session.commit()
    project_expo2010.update_schedule_timestamps()
    return sess


def test_project_no_featured_schedule(project_expo2010: models.Project) -> None:
    """Project does not have a featured schedule when it's without sessions."""
    assert project_expo2010.schedule_start_at is None
    assert project_expo2010.schedule_end_at is None
    assert project_expo2010.features.show_featured_schedule is False


@pytest.mark.usefixtures('session_yesterday')
def test_project_past_schedule(project_expo2010: models.Project) -> None:
    """Project that has sessions in the past won't show schedule."""
    assert project_expo2010.features.show_featured_schedule is False


@pytest.mark.usefixtures('session_now')
def test_project_current_schedule(project_expo2010: models.Project) -> None:
    """Project that has ongoing sessions will show schedule."""
    assert project_expo2010.features.show_featured_schedule is True


@pytest.mark.usefixtures('session_tomorrow')
def test_project_upcoming_schedule(project_expo2010: models.Project) -> None:
    """Project that has upcoming sessions will show schedule."""
    assert project_expo2010.features.show_featured_schedule is True


@pytest.mark.usefixtures('session_later')
def test_project_later_schedule(project_expo2010: models.Project) -> None:
    """Project that has later sessions won't show schedule."""
    assert project_expo2010.features.show_featured_schedule is False
