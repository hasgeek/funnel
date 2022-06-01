from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models import MEMBERSHIP_RECORD_TYPE, ProjectCrewMembership


def test_project_crew_membership(db_session, new_user, new_user_owner, new_project):
    """Test that project crew members get their roles from ProjectCrewMembership."""
    # new_user is profile admin
    assert 'admin' in new_project.profile.roles_for(new_user_owner)
    # but it has no role in the project yet
    assert (
        'editor'
        not in new_project.roles_for(  # pylint: disable=protected-access
            new_user_owner
        )._contents()
    )
    assert 'promoter' not in new_project.roles_for(new_user_owner)
    assert 'usher' not in new_project.roles_for(new_user_owner)

    previous_membership = (
        ProjectCrewMembership.query.filter(ProjectCrewMembership.is_active)
        .filter_by(project=new_project, user=new_user_owner)
        .first()
    )
    assert previous_membership is None

    new_membership = ProjectCrewMembership(
        parent=new_project, user=new_user_owner, is_editor=True
    )
    db_session.add(new_membership)
    db_session.commit()

    assert 'editor' in new_project.roles_for(new_user_owner)
    assert new_membership.is_active
    assert new_membership in new_project.active_crew_memberships
    assert new_membership.record_type == MEMBERSHIP_RECORD_TYPE.DIRECT_ADD

    # only one membership can be active for a user at a time.
    # so adding a new membership without revoking the previous one
    # will raise IntegrityError in database.
    new_membership_without_revoke = ProjectCrewMembership(
        parent=new_project, user=new_user, is_promoter=True
    )
    db_session.add(new_membership_without_revoke)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # let's revoke previous membership
    previous_membership2 = (
        ProjectCrewMembership.query.filter(ProjectCrewMembership.is_active)
        .filter_by(project=new_project, user=new_user)
        .first()
    )
    previous_membership2.revoke(actor=new_user_owner)
    db_session.commit()

    assert previous_membership2 not in new_project.active_crew_memberships

    assert 'editor' not in new_project.roles_for(new_user)
    assert 'promoter' not in new_project.roles_for(new_user)
    assert 'usher' not in new_project.roles_for(new_user)

    # let's add back few more roles
    new_membership2 = ProjectCrewMembership(
        parent=new_project, user=new_user, is_promoter=True, is_usher=True
    )
    db_session.add(new_membership2)
    db_session.commit()

    assert 'editor' not in new_project.roles_for(new_user)
    assert 'promoter' in new_project.roles_for(new_user)
    assert 'usher' in new_project.roles_for(new_user)

    # let's try replacing the roles in place
    new_membership3 = new_membership2.replace(
        actor=new_user_owner, is_editor=True, is_promoter=False, is_usher=False
    )
    db_session.commit()
    assert 'editor' in new_project.roles_for(new_user)
    assert 'promoter' not in new_project.roles_for(new_user)
    assert 'usher' not in new_project.roles_for(new_user)
    assert new_membership3.record_type == MEMBERSHIP_RECORD_TYPE.AMEND

    # replace() can replace a single role as well, rest stays as they were
    new_membership4 = new_membership3.replace(actor=new_user_owner, is_usher=True)
    db_session.commit()
    assert 'editor' in new_project.roles_for(new_user)
    assert 'promoter' not in new_project.roles_for(new_user)
    assert 'usher' in new_project.roles_for(new_user)
    # offered_roles should also return all valid roles
    assert new_membership4.offered_roles == {
        'crew',
        'participant',
        'editor',
        'usher',
    }
    assert new_membership4.record_type == MEMBERSHIP_RECORD_TYPE.AMEND

    # can't replace with an unknown role
    with pytest.raises(AttributeError):
        new_membership4.replace(actor=new_user_owner, is_foobar=True)


def test_project_roles_lazy_eval(
    db_session, new_user, new_user_owner, new_organization, new_project2
):
    """Test that the lazy roles evaluator picks up membership-based roles."""
    assert 'admin' in new_organization.profile.roles_for(new_user_owner)
    assert 'admin' not in new_organization.profile.roles_for(new_user)

    assert 'profile_admin' in new_project2.roles_for(new_user_owner)
    assert 'profile_admin' not in new_project2.roles_for(new_user)
