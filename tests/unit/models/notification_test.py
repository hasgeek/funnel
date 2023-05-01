"""Tests for Notification and UserNotification models."""
# pylint: disable=possibly-unused-variable

from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List, Set

from sqlalchemy.exc import IntegrityError

import pytest

from funnel import models

pytestmark = pytest.mark.filterwarnings(
    "ignore:Object of type <UserEmail> not in session"
)


@pytest.fixture(scope='session')
def notification_types(database) -> SimpleNamespace:
    class ProjectIsParent:
        document: models.db.Model  # type: ignore[name-defined]

        @property
        def preference_context(self) -> models.Profile:
            return self.document.project.profile

    class TestNewUpdateNotification(
        ProjectIsParent, models.Notification, type='update_new_test'
    ):
        """Notifications of new updates (test edition)."""

        category = models.notification_categories.participant
        description = "When a project posts an update"

        document_model = models.Update
        roles = ['project_crew', 'project_participant']

    class TestEditedUpdateNotification(
        ProjectIsParent,
        models.Notification,
        type='update_edit_test',
        shadows=TestNewUpdateNotification,
    ):
        """Notifications of edited updates (test edition)."""

        document_model = models.Update
        roles = ['project_crew', 'project_participant']

    class TestProposalReceivedNotification(
        ProjectIsParent, models.Notification, type='proposal_received_test'
    ):
        """Notifications of new proposals (test edition)."""

        category = models.notification_categories.project_crew
        description = "When my project receives a new proposal"

        document_model = models.Project
        fragment_model = models.Proposal
        roles = ['project_editor']

    database.configure_mappers()
    return SimpleNamespace(**locals())


@pytest.fixture()
def project_fixtures(db_session) -> SimpleNamespace:  # pylint: disable=too-many-locals
    """Provide users, one org and one project, for tests on them."""
    user_owner = models.User(username='user_owner', fullname="User Owner")
    user_owner.add_email('owner@example.com')

    user_editor = models.User(username='user_editor', fullname="User Editor")
    user_editor.add_email('editor@example.com')
    user_editor_phone = models.UserPhone(user=user_editor, phone='+12345678900')

    user_participant = models.User(
        username='user_participant', title="User Participant"
    )

    user_cancelled_participant = models.User(
        username='user_cancelled_participant', title="User Cancelled Participant"
    )
    user_bystander = models.User(username='user_bystander', title="User Bystander")
    user_suspended = models.User(username='user_suspended', title="User Suspended")
    user_suspended.add_email('suspended@example.com')

    org = models.Organization(
        name='notifications_org', title="Organization", owner=user_owner
    )

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
    project = models.Project(
        profile=profile,
        user=user_owner,
        title="Notifications project",
        tagline="Test notification delivery",
    )
    db_session.add(project)
    db_session.add(
        models.ProjectCrewMembership(
            project=project, subject=user_editor, is_editor=True
        )
    )
    rsvp_y = models.Rsvp(project=project, user=user_participant)
    rsvp_y.rsvp_yes()
    rsvp_n = models.Rsvp(project=project, user=user_cancelled_participant)
    rsvp_n.rsvp_yes()
    rsvp_n.rsvp_no()
    rsvp_suspended = models.Rsvp(project=project, user=user_suspended)
    rsvp_suspended.rsvp_yes()
    user_suspended.mark_suspended()
    db_session.add_all([rsvp_y, rsvp_n, rsvp_suspended])
    db_session.commit()

    refresh_attrs = [
        attr for attr in locals().values() if isinstance(attr, models.db.Model)
    ]

    def refresh():
        for attr in refresh_attrs:
            db_session.add(attr)

    return SimpleNamespace(**locals())


def test_project_roles(project_fixtures) -> None:
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


@pytest.fixture()
def update(project_fixtures, db_session) -> models.Update:
    """Publish an update as a fixture."""
    new_update = models.Update(
        project=project_fixtures.project,
        user=project_fixtures.user_editor,
        title="New update",
        body="New update body",
    )
    db_session.add(new_update)
    db_session.commit()
    new_update.publish(project_fixtures.user_editor)
    db_session.commit()
    return new_update


def test_update_roles(project_fixtures, update) -> None:
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
) -> None:
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

    load_notification = models.Notification.query.first()
    assert isinstance(load_notification, models.Notification)
    assert isinstance(load_notification, notification_types.TestNewUpdateNotification)
    assert not isinstance(
        load_notification, notification_types.TestProposalReceivedNotification
    )
    assert load_notification == notification

    # Extract all the user notifications and confirm they're correctly assigned
    user_notifications = list(notification.dispatch())
    # We got user assignees
    assert user_notifications
    # A second call to dispatch() will yield nothing
    assert not list(notification.dispatch())

    # Notifications are issued strictly in the order specified in cls.roles
    role_order: List[str] = []
    for un in user_notifications:
        if un.role in role_order:
            assert role_order[-1] == un.role
        else:
            role_order.append(un.role)

    assert role_order == ['project_crew', 'project_participant']

    # Notifications are correctly assigned by priority of role
    role_users: Dict[str, Set[models.User]] = {}
    for un in user_notifications:
        role_users.setdefault(un.role, set()).add(un.user)

    assert role_users == {
        'project_crew': {project_fixtures.user_owner, project_fixtures.user_editor},
        'project_participant': {project_fixtures.user_participant},
    }
    all_recipients = {un.user for un in user_notifications}
    assert project_fixtures.user_cancelled_participant not in all_recipients
    assert project_fixtures.user_bystander not in all_recipients


def test_user_notification_preferences(notification_types, db_session) -> None:
    """Test that users have a notification_preferences dict."""
    nt = notification_types  # Short var for keeping lines within 88 columns below
    user = models.User(fullname="User")
    db_session.add(user)
    db_session.commit()
    assert user.notification_preferences == {}
    np = models.NotificationPreferences(
        notification_type=nt.TestNewUpdateNotification.pref_type,
        user=user,
    )
    db_session.add(np)
    db_session.commit()
    assert set(user.notification_preferences.keys()) == {'update_new_test'}
    assert user.notification_preferences['update_new_test'] == np
    assert user.notification_preferences['update_new_test'].user == user
    assert (
        user.notification_preferences['update_new_test'].type_cls
        == nt.TestNewUpdateNotification
    )

    # There cannot be two sets of preferences for the same notification type
    db_session.add(
        models.NotificationPreferences(
            notification_type=nt.TestNewUpdateNotification.pref_type, user=user
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Preferences cannot be set for invalid types
    with pytest.raises(ValueError, match='Invalid notification_type'):
        models.NotificationPreferences(notification_type='invalid', user=user)
    db_session.rollback()

    # Preferences can be set for other notification types though
    np2 = models.NotificationPreferences(
        notification_type=nt.TestProposalReceivedNotification.pref_type,
        user=user,
    )
    db_session.add(np2)
    db_session.commit()
    assert set(user.notification_preferences.keys()) == {
        'update_new_test',
        'proposal_received_test',
    }


def test_notification_metadata(notification_types) -> None:
    """Test that notification classes have appropriate cls_type and pref_type values."""
    assert notification_types.TestNewUpdateNotification.cls_type == 'update_new_test'
    assert notification_types.TestNewUpdateNotification.pref_type == 'update_new_test'
    assert (
        notification_types.TestEditedUpdateNotification.cls_type == 'update_edit_test'
    )
    # Shadow notification type has preference type of main class
    assert (
        notification_types.TestEditedUpdateNotification.pref_type == 'update_new_test'
    )


# TODO: Add test for dispatch notification using Notification.pref_type to determine
# whether to send the notification


def test_notification_preferences(
    notification_types, project_fixtures, update, db_session
) -> None:
    """Test whether user preferences are correctly accessed."""
    # Rather than dispatching, we'll hardcode UserNotification for each test user
    notification = notification_types.TestNewUpdateNotification(update)
    db_session.add(notification)
    db_session.commit()

    # No user has any preferences saved at this point, so enquiries will result in
    # defaults
