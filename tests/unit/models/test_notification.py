from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

import pytest

from funnel.models import (
    USER_STATUS,
    NewUpdateNotification,
    Notification,
    NotificationPreferences,
    Organization,
    Project,
    ProjectCrewMembership,
    ProposalReceivedNotification,
    Rsvp,
    Update,
    User,
    UserPhone,
)

# TODO Write custom notification types for tests. Don't test existing here.


@pytest.fixture(scope='module')
def project_fixtures(test_db_structure, test_client):
    """Provide users, one org and one project, for tests on them."""
    db = test_db_structure

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

    db.session.add_all(
        [
            user_owner,
            user_editor,
            user_editor_phone,
            user_participant,
            user_bystander,
            org,
        ]
    )
    db.session.commit()
    profile = org.profile
    project = Project(
        profile=profile,
        user=user_owner,
        title="Notifications project",
        tagline="Test notification delivery",
    )
    db.session.add(project)
    db.session.add(
        ProjectCrewMembership(project=project, user=user_editor, is_editor=True)
    )
    rsvp_y = Rsvp(project=project, user=user_participant)
    rsvp_y.rsvp_yes()
    rsvp_n = Rsvp(project=project, user=user_cancelled_participant)
    rsvp_n.rsvp_yes()
    rsvp_n.rsvp_no()
    rsvp_suspended = Rsvp(project=project, user=user_suspended)
    rsvp_suspended.rsvp_yes()
    user_suspended.status = USER_STATUS.SUSPENDED
    db.session.add_all([rsvp_y, rsvp_n, rsvp_suspended])
    db.session.commit()

    refresh_attrs = [attr for attr in locals().values() if isinstance(attr, db.Model)]

    def refresh():
        for attr in refresh_attrs:
            db.session.add(attr)

    return SimpleNamespace(**locals())


def test_project_roles(project_fixtures):
    """Test that the fixtures have roles set up correctly."""
    owner_roles = project_fixtures.project.roles_for(project_fixtures.user_owner)
    assert 'editor' in owner_roles
    assert 'concierge' in owner_roles
    assert 'crew' in owner_roles
    assert 'participant' in owner_roles

    editor_roles = project_fixtures.project.roles_for(project_fixtures.user_editor)
    assert 'editor' in editor_roles
    assert 'concierge' not in editor_roles
    assert 'crew' in editor_roles
    assert 'participant' in editor_roles

    participant_roles = project_fixtures.project.roles_for(
        project_fixtures.user_participant
    )
    assert 'editor' not in participant_roles
    assert 'concierge' not in participant_roles
    assert 'crew' not in participant_roles
    assert 'participant' in participant_roles

    cancelled_participant_roles = project_fixtures.project.roles_for(
        project_fixtures.user_cancelled_participant
    )
    assert 'editor' not in cancelled_participant_roles
    assert 'concierge' not in cancelled_participant_roles
    assert 'crew' not in cancelled_participant_roles
    assert 'participant' not in cancelled_participant_roles

    bystander_roles = project_fixtures.project.roles_for(
        project_fixtures.user_bystander
    )
    assert 'editor' not in bystander_roles
    assert 'concierge' not in bystander_roles
    assert 'crew' not in bystander_roles
    assert 'participant' not in bystander_roles


@pytest.fixture()
def update(project_fixtures, db_transaction):
    """Publish an update as a fixture."""
    db = db_transaction
    update = Update(
        project=project_fixtures.project,
        user=project_fixtures.user_editor,
        title="New update",
        body="New update body",
    )
    db.session.add(update)
    db.session.commit()
    update.publish(project_fixtures.user_editor)
    db.session.commit()
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


def test_update_notification_structure(project_fixtures, update, db_transaction):
    """Test whether a NewUpdateNotification has the appropriate structure."""
    db = db_transaction
    project_fixtures.refresh()
    notification = NewUpdateNotification(update)
    db.session.add(notification)
    db.session.commit()

    assert notification.type == 'update_new'
    assert notification.document == update
    assert notification.fragment is None
    assert notification.roles == ['project_crew', 'project_participant']
    assert notification.preference_context == project_fixtures.org.profile

    load_notification = Notification.query.first()
    assert isinstance(load_notification, Notification)
    assert isinstance(load_notification, NewUpdateNotification)
    assert not isinstance(load_notification, ProposalReceivedNotification)
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


def test_user_notification_preferences(db_transaction):
    """Test that users have a notification_preferences dict."""
    db = db_transaction
    user = User(fullname="User")
    db.session.add(user)
    db.session.commit()
    assert user.notification_preferences == {}
    np = NotificationPreferences(
        user=user, notification_type=NewUpdateNotification.cls_type
    )
    db.session.add(np)
    db.session.commit()
    assert set(user.notification_preferences.keys()) == {'update_new'}
    assert user.notification_preferences['update_new'] == np
    assert user.notification_preferences['update_new'].user == user
    assert user.notification_preferences['update_new'].type_cls == NewUpdateNotification

    # There cannot be two sets of preferences for the same notification type
    with pytest.raises(IntegrityError):
        db.session.add(
            NotificationPreferences(
                user=user, notification_type=NewUpdateNotification.cls_type
            )
        )
        db.session.commit()
    db.session.rollback()

    # Preferences cannot be set for invalid types
    with pytest.raises(ValueError):
        NotificationPreferences(user=user, notification_type='invalid')

    # Preferences can be set for other notification types though
    np2 = NotificationPreferences(
        user=user, notification_type=ProposalReceivedNotification.cls_type
    )
    db.session.add(np2)
    db.session.commit()
    assert set(user.notification_preferences.keys()) == {
        'update_new',
        'proposal_received',
    }


def test_notification_preferences(project_fixtures, update, db_transaction):
    """Test whether user preferences are correctly accessed."""
    db = db_transaction
    # Rather than dispatching, we'll hardcode UserNotification for each test user
    notification = NewUpdateNotification(update)
    db.session.add(notification)
    db.session.commit()

    # No user has any preferences saved at this point, so enquiries will result in
    # defaults
