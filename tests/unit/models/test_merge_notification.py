from datetime import timedelta
from types import SimpleNamespace

import pytest

from funnel.models import (
    Notification,
    Organization,
    OrganizationAdminMembershipNotification,
    User,
    UserNotification,
    db,
    merge_users,
)


@pytest.fixture()
def fixtures(test_client):
    db.create_all()
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
    db.session.add_all([owner, user1, user2, org])
    db.session.commit()

    membership = org.active_admin_memberships.first()

    yield SimpleNamespace(**locals())

    db.session.rollback()
    db.drop_all()


@pytest.fixture()
def notification(fixtures):
    notification = OrganizationAdminMembershipNotification(
        document=fixtures.org, fragment=fixtures.membership
    )
    db.session.add(notification)
    db.session.commit()
    return notification


@pytest.fixture()
def user1_notification(fixtures, notification):
    un = UserNotification(
        eventid=notification.eventid,
        user_id=fixtures.user1.id,
        notification_id=notification.id,
        role=OrganizationAdminMembershipNotification.roles[-1],
    )
    db.session.add(un)
    db.session.commit()
    return un


@pytest.fixture()
def user2_notification(fixtures, notification):
    un = UserNotification(
        eventid=notification.eventid,
        user_id=fixtures.user2.id,
        notification_id=notification.id,
        role=OrganizationAdminMembershipNotification.roles[-1],
    )
    db.session.add(un)
    db.session.commit()
    return un


# --- Tests ----------------------------------------------------------------------------


def test_merge_without_notifications(fixtures):
    """Merge without any notifications works."""
    assert Notification.query.count() == 0
    assert UserNotification.query.count() == 0
    merged = merge_users(fixtures.user1, fixtures.user2)
    db.session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 0
    assert UserNotification.query.count() == 0


def test_merge_with_user1_notifications(fixtures, user1_notification):
    """Merge without only user1 notifications works."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    merged = merge_users(fixtures.user1, fixtures.user2)
    db.session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    assert user1_notification.user == fixtures.user1


def test_merge_with_user2_notifications(fixtures, user2_notification):
    """Merge without only user2 notifications gets it transferred to user1."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    notification = UserNotification.query.one()
    assert notification.user == fixtures.user2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db.session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    notification = UserNotification.query.one()
    assert notification.user == fixtures.user1


def test_merge_with_dupe_notifications(
    fixtures, user1_notification, user2_notification
):
    """Merge without dupe notifications gets one deleted."""
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 2
    merged = merge_users(fixtures.user1, fixtures.user2)
    db.session.commit()
    assert merged == fixtures.user1
    assert Notification.query.count() == 1
    assert UserNotification.query.count() == 1
    assert UserNotification.query.all() == [user1_notification]
    assert user1_notification.user == fixtures.user1


# TODO: Test UserNotificationPreferences merger
