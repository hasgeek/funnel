# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from coaster.utils import utcnow
from funnel.models import Project, Session


class TestProject(object):
    def test_project_state_conditional(self, test_client, test_db):
        past_projects = Project.query.filter(Project.schedule_state.PAST).all()
        assert len(past_projects) >= 0
        upcoming_projects = Project.query.filter(Project.schedule_state.UPCOMING).all()
        assert len(upcoming_projects) >= 0

    def test_project_cfp_state_conditional(self, test_client, test_db):
        private_draft_cfp_projects = Project.query.filter(Project.cfp_state.PRIVATE_DRAFT).all()
        assert len(private_draft_cfp_projects) >= 0
        draft_cfp_projects = Project.query.filter(Project.cfp_state.DRAFT).all()
        assert len(draft_cfp_projects) >= 0
        upcoming_cfp_projects = Project.query.filter(Project.cfp_state.UPCOMING).all()
        assert len(upcoming_cfp_projects) >= 0
        open_cfp_projects = Project.query.filter(Project.cfp_state.OPEN).all()
        assert len(open_cfp_projects) >= 0
        expired_cfp_projects = Project.query.filter(Project.cfp_state.EXPIRED).all()
        assert len(expired_cfp_projects) >= 0

    def test_cfp_state_draft(self, test_client, test_db, new_profile, new_project):
        assert new_project.cfp_start_at is None
        assert new_project.state.DRAFT
        assert new_project.cfp_state.NONE
        assert not new_project.cfp_state.DRAFT
        assert new_project in new_profile.draft_projects

        new_project.open_cfp()
        test_db.session.commit()

        assert new_project.cfp_state.PUBLIC
        assert new_project.cfp_start_at is None
        assert new_project.cfp_state.DRAFT
        assert new_project in new_profile.draft_projects

        new_project.cfp_start_at = utcnow()
        test_db.session.commit()

        assert new_project.cfp_start_at is not None
        assert not new_project.cfp_state.DRAFT
        assert new_project in new_profile.draft_projects  # because project state is still draft

        new_project.publish()
        test_db.session.commit()
        assert not new_project.cfp_state.DRAFT
        assert not new_project.state.DRAFT
        assert new_project not in new_profile.draft_projects

    def test_project_dates(self, test_client, test_db, new_project):
        # without any session the project will have no start and end dates
        assert new_project.sessions.count() == 0
        assert new_project.schedule_start_at is None
        assert new_project.schedule_end_at is None
        assert new_project.datelocation == u"Test Location"

        # let's add some sessions
        start_time_a = datetime(2019, 6, 12, 12, 15, 0).replace(tzinfo=new_project.timezone)
        end_time_a = start_time_a + timedelta(hours=3)
        new_session_a = Session(
            name=u"test-session-a", title=u"Test Session A",
            project=new_project, description=u"Test description",
            speaker_bio=u"Test speaker bio", is_break=False, featured=False,
            start=start_time_a, end=end_time_a
            )
        start_time_b = start_time_a + timedelta(days=2)
        end_time_b = end_time_a + timedelta(days=2)
        new_session_b = Session(
            name=u"test-session-b", title=u"Test Session B",
            project=new_project, description=u"Test description",
            speaker_bio=u"Test speaker bio", is_break=False, featured=False,
            start=start_time_b, end=end_time_b
            )
        test_db.session.add(new_session_a)
        test_db.session.add(new_session_b)
        test_db.session.commit()

        # now project.schedule_start_at will be the first session's start date
        # and project.schedule_end_at will be the last session's end date
        assert new_project.sessions.count() == 2
        assert new_project.schedule_start_at.date() == new_session_a.start.date()
        assert new_project.schedule_end_at.date() == new_session_b.end.date()

        # both session dates are in same month, hence the format below.
        assert new_project.datelocation == u"{start_at}–{end_at} {month} {year}, {location}".format(
            start_at=start_time_a.day, end_at=end_time_b.day, month=start_time_a.strftime("%b"),
            year=end_time_b.year, location=new_project.location
            )

        # The sessions are in different months
        new_session_a.start = datetime(2019, 6, 28, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_a.end = datetime(2019, 6, 28, 14, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.start = datetime(2019, 7, 1, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.end = datetime(2019, 7, 1, 14, 15, 0).replace(tzinfo=new_project.timezone)
        test_db.session.commit()

        assert new_project.datelocation == u"{start_date} {start_month}–{end_date} {end_month} {year}, {location}".format(
            start_date=new_session_a.start.strftime("%d"), start_month=new_session_a.start.strftime("%b"),
            end_date=new_session_b.end.strftime("%d"), end_month=new_session_b.end.strftime("%b"),
            year=new_session_b.end.year, location=new_project.location
            )

        # Both sessions are on same day
        new_session_a.start = datetime(2019, 6, 28, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_a.end = datetime(2019, 6, 28, 14, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.start = datetime(2019, 6, 28, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.end = datetime(2019, 6, 28, 14, 15, 0).replace(tzinfo=new_project.timezone)
        test_db.session.commit()

        assert new_project.datelocation == u"{start_date} {end_month} {year}, {location}".format(
            start_date=new_session_a.start.strftime("%d"), end_month=new_session_b.end.strftime("%b"),
            year=new_session_b.end.year, location=new_project.location
            )

        # The sessions are in different years
        new_session_a.start = datetime(2018, 12, 28, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_a.end = datetime(2018, 12, 28, 14, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.start = datetime(2019, 1, 1, 12, 15, 0).replace(tzinfo=new_project.timezone)
        new_session_b.end = datetime(2019, 1, 1, 14, 15, 0).replace(tzinfo=new_project.timezone)
        test_db.session.commit()

        assert new_project.datelocation == u"{start_date} {start_month} {start_year}–{end_date} {end_month} {end_year}, {location}".format(
            start_date=new_session_a.start.strftime("%d"), start_month=new_session_a.start.strftime("%b"),
            end_date=new_session_b.end.strftime("%d"), end_month=new_session_b.end.strftime("%b"),
            start_year=new_session_a.start.strftime("%Y"), end_year=new_session_b.end.strftime("%Y"),
            location=new_project.location
            )


