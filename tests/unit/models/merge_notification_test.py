"""Tests for merging notifications with user account merger."""
# pylint: disable=redefined-outer-name

from datetime import timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa

from funnel import models


@pytest.fixture(scope='session')
def fixture_notification_type(database) -> Any:
    class MergeTestNotification(
        models.Notification[models.User, None], type='merge_test'
    ):
        """Test notification."""

    database.configure_mappers()
    return MergeTestNotification


@pytest.fixture()
def fixtures(db_session):
    # pylint: disable=possibly-unused-variable
    owner = models.User(
        username='owner',
        fullname="Org Owner",
    )
    user1 = models.User(
        username='user1',
        fullname="User 1",
        joined_at=sa.func.utcnow() - timedelta(days=1),
    )
    user2 = models.User(
        username='user2',
        fullname="User 2",
    )
    org = models.Organization(
        name='test_org_membership_merge', title="Organization", owner=owner
    )
    db_session.add_all([owner, user1, user2, org])
    db_session.commit()

    membership = org.active_admin_memberships.first()

    return SimpleNamespace(**locals())


@pytest.fixture()
def notification(db_session, fixtures):
    new_notification = models.OrganizationAdminMembershipNotification(
        document=fixtures.org, fragment=fixtures.membership
    )
    db_session.add(new_notification)
    db_session.commit()
    return new_notification


@pytest.fixture()
def notification_recipient1(db_session, fixtures, notification):
    nr = models.NotificationRecipient(
        eventid=notification.eventid,
        recipient_id=fixtures.user1.id,
        notification_id=notification.id,
        role=models.OrganizationAdminMembershipNotification.roles[-1],
    )
    db_session.add(nr)
    db_session.commit()
    return nr


@pytest.fixture()
def notification_recipient2(db_session, fixtures, notification):
    nr = models.NotificationRecipient(
        eventid=notification.eventid,
        recipient_id=fixtures.user2.id,
        notification_id=notification.id,
        role=models.OrganizationAdminMembershipNotification.roles[-1],
    )
    db_session.add(nr)
    db_session.commit()
    return nr


@pytest.fixture()
def user1_main_preferences(db_session, fixtures):
    prefs = models.NotificationPreferences(notification_type='', account=fixtures.user1)
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture()
def user1_test_preferences(db_session, fixtures, fixture_notification_type):
    prefs = models.NotificationPreferences(
        notification_type='merge_test', account=fixtures.user1
    )
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture()
def user2_main_preferences(db_session, fixtures):
    prefs = models.NotificationPreferences(notification_type='', account=fixtures.user2)
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture()
def user2_test_preferences(db_session, fixtures, fixture_notification_type):
    prefs = models.NotificationPreferences(
        notification_type='merge_test', account=fixtures.user2
    )
    db_session.add(prefs)
    db_session.commit()
    return prefs


# --- Tests for UserNotification -------------------------------------------------------


def test_merge_without_notifications(db_session, fixtures) -> None:
    """Merge without any notifications works."""
    assert models.Notification.query.count() == 0
    assert models.NotificationRecipient.query.count() == 0
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.Notification.query.count() == 0
    assert models.NotificationRecipient.query.count() == 0


def test_merge_with_user1_notifications(
    db_session, fixtures, notification_recipient1
) -> None:
    """Merge without only user1 notifications works."""
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 1
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 1
    assert notification_recipient1.recipient == fixtures.user1


def test_merge_with_user2_notifications(
    db_session, fixtures, notification_recipient2
) -> None:
    """Merge without only user2 notifications gets it transferred to user1."""
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 1
    new_notification = models.NotificationRecipient.query.one()
    assert new_notification.recipient == fixtures.user2
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 1
    # Since user_id is part of the primary key of UserNotification, session.commit()
    # won't refresh it. It can no longer find that pkey. Therefore we must load it
    # afresh from db for the test here
    second_notification = models.NotificationRecipient.query.one()
    assert second_notification.recipient == fixtures.user1


def test_merge_with_dupe_notifications(
    db_session, fixtures, notification_recipient1, notification_recipient2
) -> None:
    """Merge without dupe notifications gets one deleted."""
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 2
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.Notification.query.count() == 1
    assert models.NotificationRecipient.query.count() == 1
    assert models.NotificationRecipient.query.all() == [notification_recipient1]
    assert notification_recipient1.recipient == fixtures.user1


# --- Tests for NotificationPreferences ------------------------------------------------


def test_merge_with_user1_preferences(
    db_session, fixtures, user1_main_preferences, user1_test_preferences
) -> None:
    """When preferences are only on the older user's account, nothing changes."""
    assert models.NotificationPreferences.query.count() == 2
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.NotificationPreferences.query.count() == 2
    assert user1_main_preferences.account == fixtures.user1
    assert user1_test_preferences.account == fixtures.user1


def test_merge_with_user2_preferences(
    db_session, fixtures, user2_main_preferences, user2_test_preferences
) -> None:
    """When preferences are only on the newer user's account, they are transferred."""
    assert models.NotificationPreferences.query.count() == 2
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.NotificationPreferences.query.count() == 2
    assert user2_main_preferences.account == fixtures.user1
    assert user2_test_preferences.account == fixtures.user1


def test_merge_with_both_preferences(
    db_session,
    fixtures,
    user1_main_preferences,
    user1_test_preferences,
    user2_main_preferences,
    user2_test_preferences,
) -> None:
    """When preferences are for both users, the newer user's are deleted."""
    assert models.NotificationPreferences.query.count() == 4
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.NotificationPreferences.query.count() == 2
    assert set(models.NotificationPreferences.query.all()) == {
        user1_main_preferences,
        user1_test_preferences,
    }


def test_merge_with_mixed_preferences(
    db_session,
    fixtures,
    user1_main_preferences,
    user2_main_preferences,
    user2_test_preferences,
) -> None:
    """A mix of transfers and deletions can happen."""
    assert models.NotificationPreferences.query.count() == 3
    merged = models.merge_accounts(fixtures.user1, fixtures.user2)
    db_session.commit()
    assert merged == fixtures.user1
    assert models.NotificationPreferences.query.count() == 2
    assert set(models.NotificationPreferences.query.all()) == {
        user1_main_preferences,
        user2_test_preferences,
    }
    assert user1_main_preferences.account == fixtures.user1
    assert user2_test_preferences.account == fixtures.user1
