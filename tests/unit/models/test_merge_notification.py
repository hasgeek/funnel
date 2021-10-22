from datetime import timedelta
from types import SimpleNamespace

import pytest

from funnel.models import (
    Notification,
    NotificationPreferences,
    Organization,
    OrganizationAdminMembershipNotification,
    User,
    UserNotification,
    db,
    merge_users,
)


@pytest.fixture(scope='session')
def test_notification_type():
    class MergeTestNotification(Notification):
        """Test notification."""

        __mapper_args__ = {'polymorphic_identity': 'merge_test'}

    return MergeTestNotification


@pytest.fixture
def fixtures(db_session):
    owner = User(
        username='owner',
        fullname="Org Owner",
    )
    user1 = User(
        username='user1',
        fullname="User 1",
        created_at=db.func.utcnow() - timedelta(days=1),
    )
    user2 = User(
        username='user2',
        fullname="User 2",
    )
    org = Organization(
        name='test-org-membership-merge', title="Organization", owner=owner
    )
    db_session.add_all([owner, user1, user2, org])
    db_session.commit()

    membership = org.active_admin_memberships.first()

    return SimpleNamespace(**locals())


@pytest.fixture
def notification(db_session, fixtures):
    notification = OrganizationAdminMembershipNotification(
        document=fixtures.org, fragment=fixtures.membership
    )
    db_session.add(notification)
    db_session.commit()
    return notification


@pytest.fixture
def user1_notification(db_session, fixtures, notification):
    un = UserNotification(
        eventid=notification.eventid,
        user_id=fixtures.user1.id,
        notification_id=notification.id,
        role=OrganizationAdminMembershipNotification.roles[-1],
    )
    db_session.add(un)
    db_session.commit()
    return un


@pytest.fixture
def user2_notification(db_session, fixtures, notification):
    un = UserNotification(
        eventid=notification.eventid,
        user_id=fixtures.user2.id,
        notification_id=notification.id,
        role=OrganizationAdminMembershipNotification.roles[-1],
    )
    db_session.add(un)
    db_session.commit()
    return un


@pytest.fixture
def user1_main_preferences(db_session, fixtures):
    prefs = NotificationPreferences(user=fixtures.user1, notification_type='')
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture
def user1_test_preferences(db_session, fixtures, test_notification_type):
    prefs = NotificationPreferences(user=fixtures.user1, notification_type='merge_test')
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture
def user2_main_preferences(db_session, fixtures):
    prefs = NotificationPreferences(user=fixtures.user2, notification_type='')
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture
def user2_test_preferences(db_session, fixtures, test_notification_type):
    prefs = NotificationPreferences(user=fixtures.user2, notification_type='merge_test')
    db_session.add(prefs)
    db_session.commit()
    return prefs


# --- Tests for UserNotification -------------------------------------------------------


def test_merge_without_notifications(db_session, fixtures):
    """Merge without any notifications works."""
    assert Notification.query.count() == 0
    assert UserNotification.query.count() == 0
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 0
    assert UserNotification.query.count() == 0


def test_merge_with_user1_notifications(db_session, fixtures, user1_notification):
    """Merge without only user1 notifications works."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    assert user1_notification.user == fixtures.user1


def test_merge_with_user2_notifications(db_session, fixtures, user2_notification):
    """Merge without only user2 notifications gets it transferred to user1."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    notification = UserNotification.query.one()
    assert notification.user == fixtures.user2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    # Since user_id is part of the primary key of UserNotification, session.commit()
    # won't refresh it. It can no longer find that pkey. Therefore we must load it
    # afresh from db for the test here
    notification = UserNotification.query.one()
    assert notification.user == fixtures.user1


def test_merge_with_dupe_notifications(
    db_session, fixtures, user1_notification, user2_notification
):
    """Merge without dupe notifications gets one deleted."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    assert UserNotification.query.all() == [user1_notification]
    assert user1_notification.user == fixtures.user1


# --- Tests for NotificationPreferences ------------------------------------------------


def test_merge_with_user1_preferences(
    db_session, fixtures, user1_main_preferences, user1_test_preferences
):
    """When preferences are only on the older user's account, nothing changes."""
    assert NotificationPreferences.query.count() == 2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert NotificationPreferences.query.count() == 2
    assert user1_main_preferences.user == fixtures.user1
    assert user1_test_preferences.user == fixtures.user1


def test_merge_with_user2_preferences(
    db_session, fixtures, user2_main_preferences, user2_test_preferences
):
    """When preferences are only on the newer user's account, they are transferred."""
    assert NotificationPreferences.query.count() == 2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert NotificationPreferences.query.count() == 2
    assert user2_main_preferences.user == fixtures.user1
    assert user2_test_preferences.user == fixtures.user1


def test_merge_with_both_preferences(
    db_session,
    fixtures,
    user1_main_preferences,
    user1_test_preferences,
    user2_main_preferences,
    user2_test_preferences,
):
    """When preferences are for both users, the newer user's are deleted."""
    assert NotificationPreferences.query.count() == 4
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert NotificationPreferences.query.count() == 2
    assert set(NotificationPreferences.query.all()) == {
        user1_main_preferences,
        user1_test_preferences,
    }


def test_merge_with_mixed_preferences(
    db_session,
    fixtures,
    user1_main_preferences,
    user2_main_preferences,
    user2_test_preferences,
):
    """A mix of transfers and deletions can happen."""
    assert NotificationPreferences.query.count() == 3
    merged = merge_users(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert NotificationPreferences.query.count() == 2
    assert set(NotificationPreferences.query.all()) == {
        user1_main_preferences,
        user2_test_preferences,
    }
    assert user1_main_preferences.user == fixtures.user1
    assert user2_test_preferences.user == fixtures.user1
