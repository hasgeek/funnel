# -*- coding: utf-8 -*-

from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models import ProjectCrewMembership


class TestMembership(object):
    def test_crew_membership(self, test_db, new_user, new_user2, new_project):
        # new_user is profile admin
        assert 'profile_admin' in new_project.roles_for(new_user)
        # but it has no role in the project yet
        assert 'project_editor' not in new_project.roles_for(new_user)
        assert 'project_concierge' not in new_project.roles_for(new_user)
        assert 'project_usher' not in new_project.roles_for(new_user)

        previous_membership = (
            ProjectCrewMembership.query.filter(ProjectCrewMembership.active)
            .filter_by(project=new_project, user=new_user)
            .first()
        )
        assert previous_membership is None

        new_membership = ProjectCrewMembership(
            project=new_project, user=new_user, is_editor=True
        )
        test_db.session.add(new_membership)
        test_db.session.commit()

        assert 'project_editor' in new_project.roles_for(new_user)
        assert new_membership.active
        assert new_membership in new_project.active_crew_memberships

        # only one membership can be active for a user at a time.
        # so adding a new membership without revoking the previous one
        # will raise IntegrityError in database.
        new_membership_without_revoke = ProjectCrewMembership(
            project=new_project, user=new_user, is_concierge=True
        )
        test_db.session.add(new_membership_without_revoke)
        with pytest.raises(IntegrityError):
            test_db.session.commit()
        test_db.session.rollback()

        # let's revoke previous membership
        previous_membership2 = (
            ProjectCrewMembership.query.filter(ProjectCrewMembership.active)
            .filter_by(project=new_project, user=new_user)
            .first()
        )
        previous_membership2.revoke(actor=new_user2)
        test_db.session.commit()

        assert previous_membership2 not in new_project.active_crew_memberships

        assert 'project_editor' not in new_project.roles_for(new_user)
        assert 'project_concierge' not in new_project.roles_for(new_user)
        assert 'project_usher' not in new_project.roles_for(new_user)

        # let's add back few more roles
        new_membership2 = ProjectCrewMembership(
            project=new_project, user=new_user, is_concierge=True, is_usher=True
        )
        test_db.session.add(new_membership2)
        test_db.session.commit()

        assert 'project_editor' not in new_project.roles_for(new_user)
        assert 'project_concierge' in new_project.roles_for(new_user)
        assert 'project_usher' in new_project.roles_for(new_user)

        # let's try replacing the roles in place
        new_membership3 = new_membership2.replace(
            actor=new_user2, is_editor=True, is_concierge=False, is_usher=False
        )
        test_db.session.commit()
        assert 'project_editor' in new_project.roles_for(new_user)
        assert 'project_concierge' not in new_project.roles_for(new_user)
        assert 'project_usher' not in new_project.roles_for(new_user)

        # replace() can replace a single role as well, rest stays as they were
        new_membership4 = new_membership3.replace(actor=new_user2, is_usher=True)
        test_db.session.commit()
        assert 'project_editor' in new_project.roles_for(new_user)
        assert 'project_concierge' not in new_project.roles_for(new_user)
        assert 'project_usher' in new_project.roles_for(new_user)
        # offered_roles should also return all valid roles
        assert new_membership4.offered_roles() == {'project_editor', 'project_usher'}

        # can't replace with an unknown role
        with pytest.raises(AttributeError):
            new_membership2.replace(actor=new_user2, is_foobar=True)
