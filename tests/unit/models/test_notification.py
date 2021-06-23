from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models import (
    Notification,
    NotificationPreferences,
    Organization,
    Profile,
    Project,
    ProjectCrewMembership,
    Proposal,
    Rsvp,
    Update,
    User,
    UserPhone,
    db,
    notification_categories,
)


@pytest.fixture(scope='session')
def notification_types():
    class ProjectIsParent:
        document: db.Model

        @property
        def preference_context(self) -> Profile:
            return self.document.project.profile

    class TestNewUpdateNotification(ProjectIsParent, Notification):
        """Notifications of new updates (test edition)."""

        __mapper_args__ = {'polymorphic_identity': 'update_new_test'}

        category = notification_categories.participant
        description = "When a project posts an update"

        document: Update
        roles = ['project_crew', 'project_participant']

    class TestProposalReceivedNotification(ProjectIsParent, Notification):
        """Notifications of new proposals (test edition)."""

        __mapper_args__ = {'polymorphic_identity': 'proposal_received_test'}

        category = notification_categories.project_crew
        description = "When my project receives a new proposal"

        document: Project
        fragment: Proposal
        roles = ['project_editor']

    return SimpleNamespace(**locals())


@pytest.fixture
def project_fixtures(db_session):
    """Provide users, one org and one project, for tests on them."""
    user_owner = User(username='user-owner', fullname="User Owner")
    user_owner.add_email('owner@example.com')

    user_editor = User(username='user-editor', fullname="User Editor")
    user_editor.add_email('editor@example.com')
    user_editor_phone = UserPhone(user=user_editor, phone='+1234567890')

    user_participant = User(username='user-participant', title="User Participant")

    user_cancelled_participant = User(
        username='user-cancelled-participant', title="User Cancelled Participant"
    )
    user_bystander = User(username='user-bystander', title="User Bystander")
    user_suspended = User(username='user-suspended', title="User Suspended")
    user_suspended.add_email('suspended@example.com')

    org = Organization(name='notifications-org', title="Organization", owner=user_owner)

    db_session.add_all(
        [
            user_owner,
            user_editor,
            user_editor_phone,
            user_participant,
            user_bystander,
            org,
        ]
    )
    db_session.commit()
    profile = org.profile
    project = Project(
        profile=profile,
        user=user_owner,
        title="Notifications project",
        tagline="Test notification delivery",
    )
    db_session.add(project)
    db_session.add(
        ProjectCrewMembership(project=project, user=user_editor, is_editor=True)
    )
    rsvp_y = Rsvp(project=project, user=user_participant)
    rsvp_y.rsvp_yes(subscribe_comments=True)
    rsvp_n = Rsvp(project=project, user=user_cancelled_participant)
    rsvp_n.rsvp_yes(subscribe_comments=True)
    rsvp_n.rsvp_no()
    rsvp_suspended = Rsvp(project=project, user=user_suspended)
    rsvp_suspended.rsvp_yes(subscribe_comments=True)
    user_suspended.mark_suspended()
    db_session.add_all([rsvp_y, rsvp_n, rsvp_suspended])
    db_session.commit()

    refresh_attrs = [attr for attr in locals().values() if isinstance(attr, db.Model)]

    def refresh():
        for attr in refresh_attrs:
            db_session.add(attr)

    return SimpleNamespace(**locals())


def test_project_roles(project_fixtures):
    """Test that the fixtures have roles set up correctly."""
    owner_roles = project_fixtures.project.roles_for(project_fixtures.user_owner)
    assert 'editor' in owner_roles
    assert 'promoter' in owner_roles
    assert 'crew' in owner_roles
    assert 'participant' in owner_roles

    editor_roles = project_fixtures.project.roles_for(project_fixtures.user_editor)
    assert 'editor' in editor_roles
    assert 'promoter' not in editor_roles
    assert 'crew' in editor_roles
    assert 'participant' in editor_roles

    participant_roles = project_fixtures.project.roles_for(
        project_fixtures.user_participant
    )
    assert 'editor' not in participant_roles
    assert 'promoter' not in participant_roles
    assert 'crew' not in participant_roles
    assert 'participant' in participant_roles

    cancelled_participant_roles = project_fixtures.project.roles_for(
        project_fixtures.user_cancelled_participant
    )
    assert 'editor' not in cancelled_participant_roles
    assert 'promoter' not in cancelled_participant_roles
    assert 'crew' not in cancelled_participant_roles
    assert 'participant' not in cancelled_participant_roles

    bystander_roles = project_fixtures.project.roles_for(
        project_fixtures.user_bystander
    )
    assert 'editor' not in bystander_roles
    assert 'promoter' not in bystander_roles
    assert 'crew' not in bystander_roles
    assert 'participant' not in bystander_roles


@pytest.fixture
def update(project_fixtures, db_session):
    """Publish an update as a fixture."""
    update = Update(
        project=project_fixtures.project,
        user=project_fixtures.user_editor,
        title="New update",
        body="New update body",
    )
    db_session.add(update)
    db_session.commit()
    update.publish(project_fixtures.user_editor)
    db_session.commit()
    return update


def test_update_roles(project_fixtures, update):
    """Test whether Update grants the project_* roles to users."""
    owner_roles = update.roles_for(project_fixtures.user_owner)
    assert 'project_editor' in owner_roles
    assert 'project_crew' in owner_roles
    assert 'project_participant' in owner_roles

    editor_roles = update.roles_for(project_fixtures.user_editor)
    assert 'project_editor' in editor_roles
    assert 'project_crew' in editor_roles
    assert 'project_participant' in editor_roles

    participant_roles = update.roles_for(project_fixtures.user_participant)
    assert 'project_editor' not in participant_roles
    assert 'project_crew' not in participant_roles
    assert 'project_participant' in participant_roles

    cancelled_participant_roles = update.roles_for(
        project_fixtures.user_cancelled_participant
    )
    assert 'project_editor' not in cancelled_participant_roles
    assert 'project_crew' not in cancelled_participant_roles
    assert 'project_participant' not in cancelled_participant_roles

    bystander_roles = update.roles_for(project_fixtures.user_bystander)
    assert 'project_editor' not in bystander_roles
    assert 'project_crew' not in bystander_roles
    assert 'project_participant' not in bystander_roles


def test_update_notification_structure(
    notification_types, project_fixtures, update, db_session
):
    """Test whether a NewUpdateNotification has the appropriate structure."""
    project_fixtures.refresh()
    notification = notification_types.TestNewUpdateNotification(update)
    db_session.add(notification)
    db_session.commit()

    assert notification.type == 'update_new_test'
    assert notification.document == update
    assert notification.fragment is None
    assert notification.roles == ['project_crew', 'project_participant']
    assert notification.preference_context == project_fixtures.org.profile

    load_notification = Notification.query.first()
    assert isinstance(load_notification, Notification)
    assert isinstance(load_notification, notification_types.TestNewUpdateNotification)
    assert not isinstance(
        load_notification, notification_types.TestProposalReceivedNotification
    )
    assert load_notification == notification

    # Extract all the user notifications and confirm they're correctly assigned
    user_notifications = list(notification.dispatch())
    # We got user assignees
    assert user_notifications != []
    # A second call to dispatch() will yield nothing
    assert list(notification.dispatch()) == []

    # Notifications are issued strictly in the order specified in cls.roles
    role_order = []
    for un in user_notifications:
        if un.role in role_order:
            assert role_order[-1] == un.role
        else:
            role_order.append(un.role)

    assert role_order == ['project_crew', 'project_participant']

    # Notifications are correctly assigned by priority of role
    role_users = {}
    for un in user_notifications:
        role_users.setdefault(un.role, set()).add(un.user)

    assert role_users == {
        'project_crew': {project_fixtures.user_owner, project_fixtures.user_editor},
        'project_participant': {project_fixtures.user_participant},
    }
    all_recipients = {un.user for un in user_notifications}
    assert project_fixtures.user_cancelled_participant not in all_recipients
    assert project_fixtures.user_bystander not in all_recipients


def test_user_notification_preferences(notification_types, db_session):
    """Test that users have a notification_preferences dict."""
    user = User(fullname="User")
    db_session.add(user)
    db_session.commit()
    assert user.notification_preferences == {}
    np = NotificationPreferences(
        user=user,
        notification_type=notification_types.TestNewUpdateNotification.cls_type(),
    )
    db_session.add(np)
    db_session.commit()
    assert set(user.notification_preferences.keys()) == {'update_new_test'}
    assert user.notification_preferences['update_new_test'] == np
    assert user.notification_preferences['update_new_test'].user == user
    assert (
        user.notification_preferences['update_new_test'].type_cls
        == notification_types.TestNewUpdateNotification
    )

    # There cannot be two sets of preferences for the same notification type
    with pytest.raises(IntegrityError):
        db_session.add(
            NotificationPreferences(
                user=user,
                notification_type=notification_types.TestNewUpdateNotification.cls_type(),
            )
        )
        db_session.commit()
    db_session.rollback()

    # Preferences cannot be set for invalid types
    with pytest.raises(ValueError):
        NotificationPreferences(user=user, notification_type='invalid')
    db_session.rollback()

    # Preferences can be set for other notification types though
    np2 = NotificationPreferences(
        user=user,
        notification_type=notification_types.TestProposalReceivedNotification.cls_type(),
    )
    db_session.add(np2)
    db_session.commit()
    assert set(user.notification_preferences.keys()) == {
        'update_new_test',
        'proposal_received_test',
    }


def test_notification_preferences(
    notification_types, project_fixtures, update, db_session
):
    """Test whether user preferences are correctly accessed."""
    # Rather than dispatching, we'll hardcode UserNotification for each test user
    notification = notification_types.TestNewUpdateNotification(update)
    db_session.add(notification)
    db_session.commit()

    # No user has any preferences saved at this point, so enquiries will result in
    # defaults
