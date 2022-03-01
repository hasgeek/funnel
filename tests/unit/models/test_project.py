from datetime import datetime, timedelta

import pytest

from coaster.utils import utcnow
from funnel.models import Organization, ProjectRedirect, Proposal, Session


def invalidate_cache(project):
    for attr in (
        'datelocation',
        'schedule_start_at_localized',
        'schedule_end_at_localized',
        'start_at_localized',
        'end_at_localized',
    ):
        try:
            delattr(project, attr)
        except KeyError:
            # Not in cache, ignore
            pass


def test_cfp_state_draft(db_session, new_organization, new_project):
    assert new_project.cfp_start_at is None
    assert new_project.state.DRAFT
    assert new_project.cfp_state.NONE
    assert not new_project.cfp_state.DRAFT
    assert new_project in new_organization.profile.draft_projects

    new_project.open_cfp()
    db_session.commit()

    assert new_project.cfp_state.PUBLIC
    # Start date is automatically set by open_cfp to utcnow()
    assert new_project.cfp_start_at > utcnow() - timedelta(minutes=1)
    assert not new_project.cfp_state.DRAFT
    assert new_project.cfp_state.OPEN
    assert new_project in new_organization.profile.draft_projects

    new_project.cfp_start_at = utcnow()
    db_session.commit()

    assert new_project.cfp_start_at is not None
    assert not new_project.cfp_state.DRAFT
    assert (
        new_project in new_organization.profile.draft_projects
    )  # because project state is still draft

    new_project.publish()
    db_session.commit()
    assert not new_project.cfp_state.DRAFT
    assert not new_project.state.DRAFT
    assert new_project not in new_organization.profile.draft_projects


def test_project_dates(db_session, new_project):
    # without any session the project will have no start and end dates
    assert new_project.sessions.count() == 0
    assert new_project.schedule_start_at is None
    assert new_project.schedule_end_at is None
    assert new_project.datelocation == "Test Location"

    # let's add some sessions
    start_time_a = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 12, 12, 15, 0))
    )
    end_time_a = start_time_a + timedelta(hours=3)
    new_session_a = Session(
        name="test-session-a",
        title="Test Session A",
        project=new_project,
        description="Test description",
        is_break=False,
        featured=False,
        start_at=start_time_a,
        end_at=end_time_a,
    )
    start_time_b = start_time_a + timedelta(days=2)
    end_time_b = end_time_a + timedelta(days=2)
    new_session_b = Session(
        name="test-session-b",
        title="Test Session B",
        project=new_project,
        description="Test description",
        is_break=False,
        featured=False,
        start_at=start_time_b,
        end_at=end_time_b,
    )
    db_session.add(new_session_a)
    db_session.add(new_session_b)
    db_session.commit()
    new_project.update_schedule_timestamps()

    # now project.schedule_start_at will be the first session's start date
    # and project.schedule_end_at will be the last session's end date
    assert new_project.sessions.count() == 2
    assert new_project.schedule_start_at.date() == new_session_a.start_at.date()
    assert new_project.schedule_end_at.date() == new_session_b.end_at.date()
    assert new_project.start_at.date() == new_session_a.start_at.date()
    assert new_project.end_at.date() == new_session_b.end_at.date()

    # Invalidate property cache
    invalidate_cache(new_project)

    # both session dates are in same month, hence the format below.
    assert (
        new_project.datelocation
        == "{start_at}–{end_at} {month} {year}, {location}".format(
            start_at=start_time_a.day,
            end_at=end_time_b.day,
            month=start_time_a.strftime("%b"),
            year=end_time_b.year,
            location=new_project.location,
        )
    )

    # The sessions are in different months
    new_session_a.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 12, 15, 0))
    )
    new_session_a.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 14, 15, 0))
    )
    new_session_b.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 7, 1, 12, 15, 0))
    )
    new_session_b.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 7, 1, 14, 15, 0))
    )
    db_session.commit()
    new_project.update_schedule_timestamps()

    # Invalidate property cache
    invalidate_cache(new_project)

    assert (
        new_project.datelocation
        == "{start_date} {start_month}–{end_date} {end_month} {year}, {location}".format(
            start_date=new_session_a.start_at.strftime("%d"),
            start_month=new_session_a.start_at.strftime("%b"),
            end_date=new_session_b.end_at.strftime("%d"),
            end_month=new_session_b.end_at.strftime("%b"),
            year=new_session_b.end_at.year,
            location=new_project.location,
        )
    )

    # Both sessions are on same day
    new_session_a.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 12, 15, 0))
    )
    new_session_a.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 14, 15, 0))
    )
    new_session_b.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 12, 15, 0))
    )
    new_session_b.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 6, 28, 14, 15, 0))
    )
    db_session.commit()
    new_project.update_schedule_timestamps()

    # Invalidate property cache
    invalidate_cache(new_project)

    assert (
        new_project.datelocation
        == "{start_date} {end_month} {year}, {location}".format(
            start_date=new_session_a.start_at.strftime("%d"),
            end_month=new_session_b.end_at.strftime("%b"),
            year=new_session_b.end_at.year,
            location=new_project.location,
        )
    )

    # The sessions are in different years
    new_session_a.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2018, 12, 28, 12, 15, 0))
    )
    new_session_a.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2018, 12, 28, 14, 15, 0))
    )
    new_session_b.start_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 1, 1, 12, 15, 0))
    )
    new_session_b.end_at = new_project.timezone.normalize(
        new_project.timezone.localize(datetime(2019, 1, 1, 14, 15, 0))
    )
    db_session.commit()
    new_project.update_schedule_timestamps()

    # Invalidate property cache
    invalidate_cache(new_project)

    assert (
        new_project.datelocation
        == "{start_date} {start_month} {start_year}–{end_date} {end_month} {end_year}, {location}".format(
            start_date=new_session_a.start_at.strftime("%d"),
            start_month=new_session_a.start_at.strftime("%b"),
            end_date=new_session_b.end_at.strftime("%d"),
            end_month=new_session_b.end_at.strftime("%b"),
            start_year=new_session_a.start_at.strftime("%Y"),
            end_year=new_session_b.end_at.strftime("%Y"),
            location=new_project.location,
        )
    )


@pytest.fixture
def second_organization(db_session, new_user2):
    org2 = Organization(owner=new_user2, title="Second test org", name='test-org-2')
    db_session.add(org2)
    db_session.commit()
    return org2


def test_project_rename(
    db_session, new_organization, second_organization, new_project, new_project2
):
    # The project has a default name from the fixture, and there is no redirect
    assert new_project.name == 'test-project'
    assert new_project.profile == new_organization.profile
    redirect = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='test-project'
    ).one_or_none()
    assert redirect is None

    # Renaming the project automatically creates a redirect
    new_project.title = "Renamed project"
    new_project.make_name()
    assert new_project.name == 'renamed-project'
    redirect = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='test-project'
    ).one_or_none()
    assert redirect is not None
    assert redirect.project == new_project

    # However, using an invalid name is blocked
    with pytest.raises(ValueError):
        new_project.name = None

    with pytest.raises(ValueError):
        new_project.name = 'this is invalid'

    # Changing project also creates a redirect from the old project
    redirect2 = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='renamed-project'
    ).one_or_none()
    assert redirect2 is None

    new_project.profile = second_organization.profile
    redirect2 = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='renamed-project'
    ).one_or_none()
    assert redirect2 is not None
    assert redirect2.project == new_project
    assert redirect2 != redirect

    # If another project reuses a name and then vacates it, the original redirect will
    # now point to the new project
    new_project2.name = 'test-project'
    # The existing redirect is not touched by this, as the project takes priority
    new_redirect = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='test-project'
    ).one_or_none()
    assert new_redirect is not None
    assert new_redirect == redirect
    assert new_redirect.project == new_project

    # But renaming out will reuse the existing redirect to point to the new project
    new_project2.name = 'renamed-away'
    new_redirect = ProjectRedirect.query.filter_by(
        profile=new_organization.profile, name='test-project'
    ).one_or_none()
    assert new_redirect is not None
    assert new_redirect == redirect
    assert new_redirect.project == new_project2


def test_project_featured_proposal(db_session, user_twoflower, project_expo2010):
    # `has_featured_proposals` returns None if the project has no proposals
    assert project_expo2010.has_featured_proposals is False

    # A proposal is created, default state is `Submitted`
    proposal = Proposal(
        project=project_expo2010,
        user=user_twoflower,
        title="Test Proposal",
        body="Test body",
        description="Test",
        featured=True,
    )
    db_session.add(proposal)
    db_session.commit()

    assert project_expo2010.has_featured_proposals is True
