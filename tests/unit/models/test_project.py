# -*- coding: utf-8 -*-

from datetime import timedelta
from coaster.utils import utcnow
from funnel.models import Project, Session


class TestProject(object):
    def test_project_state_conditional(self, test_client, test_db):
        past_projects = Project.query.filter(Project.state.PAST).all()
        assert len(past_projects) >= 0
        upcoming_projects = Project.query.filter(Project.state.UPCOMING).all()
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

        # let's add some sessions
        start_time_a = utcnow()
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
