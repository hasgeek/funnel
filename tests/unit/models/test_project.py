# -*- coding: utf-8 -*-

from funnel.models import Project


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

    def test_draft_projects(self, test_client, test_db, new_profile, new_project):
        assert new_project.state.DRAFT
        assert new_project in new_profile.draft_projects
        assert new_project not in new_profile.listed_projects

        new_project.publish()
        test_db.session.commit()

        assert new_project.state.PUBLISHED
        assert new_project not in new_profile.draft_projects
        assert new_project in new_profile.listed_projects

