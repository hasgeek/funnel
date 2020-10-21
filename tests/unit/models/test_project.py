from datetime import datetime, timedelta

# FIXME: For unknown reasons, mypy thinks this attribute does not exist
from werkzeug.utils import invalidate_cached_property  # type: ignore[attr-defined]

import pytest

from coaster.utils import utcnow
from funnel.models import Organization, Project, ProjectRedirect, Session


def test_project_state_conditional(test_db):
    past_projects = Project.query.filter(Project.schedule_state.PAST).all()
    assert len(past_projects) >= 0
    upcoming_projects = Project.query.filter(Project.schedule_state.UPCOMING).all()
    assert len(upcoming_projects) >= 0


def test_project_cfp_state_conditional(test_db):
    private_draft_cfp_projects = Project.query.filter(
        Project.cfp_state.PRIVATE_DRAFT
    ).all()
    assert len(private_draft_cfp_projects) >= 0
    draft_cfp_projects = Project.query.filter(Project.cfp_state.DRAFT).all()
    assert len(draft_cfp_projects) >= 0
    upcoming_cfp_projects = Project.query.filter(Project.cfp_state.UPCOMING).all()
    assert len(upcoming_cfp_projects) >= 0
    open_cfp_projects = Project.query.filter(Project.cfp_state.OPEN).all()
    assert len(open_cfp_projects) >= 0
    expired_cfp_projects = Project.query.filter(Project.cfp_state.EXPIRED).all()
    assert len(expired_cfp_projects) >= 0


def test_cfp_state_draft(test_db, new_organization, new_project):
    assert new_project.cfp_start_at is None
    assert new_project.state.DRAFT
    assert new_project.cfp_state.NONE
    assert not new_project.cfp_state.DRAFT
    assert new_project in new_organization.profile.draft_projects

    new_project.open_cfp()
    test_db.session.commit()

    assert new_project.cfp_state.PUBLIC
    assert new_project.cfp_start_at is None
    assert new_project.cfp_state.DRAFT
    assert new_project in new_organization.profile.draft_projects

    new_project.cfp_start_at = utcnow()
    test_db.session.commit()

    assert new_project.cfp_start_at is not None
    assert not new_project.cfp_state.DRAFT
    assert (
        new_project in new_organization.profile.draft_projects
    )  # because project state is still draft

    new_project.publish()
    test_db.session.commit()
    assert not new_project.cfp_state.DRAFT
    assert not new_project.state.DRAFT
    assert new_project not in new_organization.profile.draft_projects


def test_project_dates(test_db, new_project):
    # without any session the project will have no start and end dates
    assert new_project.sessions.count() == 0
    assert new_project.schedule_start_at is None
    assert new_project.schedule_end_at is None
    assert new_project.datelocation == "Test Location"

    # let's add some sessions
    start_time_a = datetime(2019, 6, 12, 12, 15, 0).replace(tzinfo=new_project.timezone)
    end_time_a = start_time_a + timedelta(hours=3)
    new_session_a = Session(
        name="test-session-a",
        title="Test Session A",
        project=new_project,
        description="Test description",
        speaker_bio="Test speaker bio",
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
        speaker_bio="Test speaker bio",
        is_break=False,
        featured=False,
        start_at=start_time_b,
        end_at=end_time_b,
    )
    test_db.session.add(new_session_a)
    test_db.session.add(new_session_b)
    test_db.session.commit()

    # now project.schedule_start_at will be the first session's start date
    # and project.schedule_end_at will be the last session's end date
    assert new_project.sessions.count() == 2
    assert new_project.schedule_start_at.date() == new_session_a.start_at.date()
    assert new_project.schedule_end_at.date() == new_session_b.end_at.date()

    # Invalidate property cache
    invalidate_cached_property(new_project, 'datelocation')
    invalidate_cached_property(new_project, 'schedule_start_at_localized')
    invalidate_cached_property(new_project, 'schedule_end_at_localized')

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
    new_session_a.start_at = datetime(2019, 6, 28, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_a.end_at = datetime(2019, 6, 28, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.start_at = datetime(2019, 7, 1, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.end_at = datetime(2019, 7, 1, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    test_db.session.commit()

    # Invalidate property cache
    invalidate_cached_property(new_project, 'datelocation')
    invalidate_cached_property(new_project, 'schedule_start_at_localized')
    invalidate_cached_property(new_project, 'schedule_end_at_localized')

    assert new_project.datelocation == "{start_date} {start_month}–{end_date} {end_month} {year}, {location}".format(
        start_date=new_session_a.start_at.strftime("%d"),
        start_month=new_session_a.start_at.strftime("%b"),
        end_date=new_session_b.end_at.strftime("%d"),
        end_month=new_session_b.end_at.strftime("%b"),
        year=new_session_b.end_at.year,
        location=new_project.location,
    )

    # Both sessions are on same day
    new_session_a.start_at = datetime(2019, 6, 28, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_a.end_at = datetime(2019, 6, 28, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.start_at = datetime(2019, 6, 28, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.end_at = datetime(2019, 6, 28, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    test_db.session.commit()

    # Invalidate property cache
    invalidate_cached_property(new_project, 'datelocation')
    invalidate_cached_property(new_project, 'schedule_start_at_localized')
    invalidate_cached_property(new_project, 'schedule_end_at_localized')

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
    new_session_a.start_at = datetime(2018, 12, 28, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_a.end_at = datetime(2018, 12, 28, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.start_at = datetime(2019, 1, 1, 12, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    new_session_b.end_at = datetime(2019, 1, 1, 14, 15, 0).replace(
        tzinfo=new_project.timezone
    )
    test_db.session.commit()

    # Invalidate property cache
    invalidate_cached_property(new_project, 'datelocation')
    invalidate_cached_property(new_project, 'schedule_start_at_localized')
    invalidate_cached_property(new_project, 'schedule_end_at_localized')

    assert new_project.datelocation == "{start_date} {start_month} {start_year}–{end_date} {end_month} {end_year}, {location}".format(
        start_date=new_session_a.start_at.strftime("%d"),
        start_month=new_session_a.start_at.strftime("%b"),
        end_date=new_session_b.end_at.strftime("%d"),
        end_month=new_session_b.end_at.strftime("%b"),
        start_year=new_session_a.start_at.strftime("%Y"),
        end_year=new_session_b.end_at.strftime("%Y"),
        location=new_project.location,
    )


@pytest.fixture()
def second_organization(test_db, new_user2):
    org2 = Organization(owner=new_user2, title="Second test org", name='test-org-2')
    test_db.session.add(org2)
    test_db.session.commit()
    return org2


def test_project_rename(
    test_db, new_organization, second_organization, new_project, new_project2
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
