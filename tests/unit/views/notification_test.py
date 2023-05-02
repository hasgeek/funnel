"""Test Notification views."""

from urllib.parse import urlsplit

from flask import url_for

import pytest

from funnel import models


@pytest.fixture()
def phone_vetinari(db_session, user_vetinari):
    """Add a phone number to user_vetinari."""
    accountphone = user_vetinari.add_phone('+12345678900')
    db_session.add(accountphone)
    db_session.commit()
    return accountphone


@pytest.fixture()
def notification_prefs_vetinari(db_session, user_vetinari):
    """Add main notification preferences for user_vetinari."""
    prefs = models.NotificationPreferences(
        notification_type='',
        user=user_vetinari,
        by_email=True,
        by_sms=True,
        by_webpush=True,
        by_telegram=True,
        by_whatsapp=True,
    )
    db_session.add(prefs)
    db_session.commit()
    return prefs


@pytest.fixture()
def project_update(db_session, user_vetinari, project_expo2010):
    """Create an update to add a notification for."""
    db_session.commit()
    update = models.Update(
        project=project_expo2010,
        user=user_vetinari,
        title="New update",
        body="New update body",
    )
    db_session.add(update)
    db_session.commit()
    update.publish(user_vetinari)
    db_session.commit()
    return update


@pytest.fixture()
def update_user_notification(db_session, user_vetinari, project_update):
    """Get a user notification for the update fixture."""
    notification = models.NewUpdateNotification(project_update)
    db_session.add(notification)
    db_session.commit()

    # Extract all the user notifications
    all_user_notifications = list(notification.dispatch())
    db_session.commit()
    # There should be only one, assigned to Vetinari, but we'll let the test confirm
    return all_user_notifications[0]


def test_user_notification_is_for_user_vetinari(
    update_user_notification, user_vetinari
) -> None:
    """Confirm the test notification is for the test user fixture."""
    assert update_user_notification.user == user_vetinari


@pytest.fixture()
def unsubscribe_sms_short_url(
    update_user_notification, phone_vetinari, notification_prefs_vetinari
):
    """Get an unsubscribe URL for the SMS notification."""
    return update_user_notification.views.render.unsubscribe_short_url('sms')


def test_unsubscribe_view_is_well_formatted(unsubscribe_sms_short_url) -> None:
    """Confirm the SMS unsubscribe URL is well formatted."""
    prefix = 'https://bye.test/'
    assert unsubscribe_sms_short_url.startswith(prefix)
    assert len(unsubscribe_sms_short_url) == len(prefix) + 4  # 4 char random value


def test_unsubscribe_sms_view(
    app, client, unsubscribe_sms_short_url, user_vetinari
) -> None:
    """Confirm the unsubscribe URL renders a form."""
    unsub_url = url_for(
        'notification_unsubscribe_short',
        token=urlsplit(unsubscribe_sms_short_url).path[1:],
        _external=True,
    )

    # Get the unsubscribe URL. This should cause a cookie to be set, with a
    # redirect to the same URL and `?cookietest=1` appended
    rv = client.get(unsub_url)
    assert rv.status_code == 302
    assert rv.location.startswith(unsub_url)
    assert rv.location.endswith('cookietest=1')

    # Follow the redirect. This will cause yet another redirect
    rv = client.get(rv.location)
    assert rv.status_code == 302
    # Werkzeug 2.1 defaults to relative URLs in redirects as per the change in RFC 7231:
    # https://datatracker.ietf.org/doc/html/rfc7231#section-7.1.2
    # https://github.com/pallets/werkzeug/issues/2352
    # Earlier versions of Werkzeug defaulted to RFC 2616 behaviour for an absolute URL:
    # https://datatracker.ietf.org/doc/html/rfc2616#section-14.30
    # This test will fail on Werkzeug < 2.1
    assert rv.location == url_for('notification_unsubscribe_do', _external=False)

    # This time we'll get the unsubscribe form.
    rv = client.get(rv.location)
    assert rv.status_code == 200

    # Assert the user has SMS notifications enabled, and the form agrees
    assert user_vetinari.main_notification_preferences.by_sms is True
    form = rv.form('form-unsubscribe-preferences')
    assert form.fields['main'] == 'y'
    form.fields['main'] = False
    rv = form.submit(client)
    # We'll now get an acknowledgement
    assert rv.status_code == 200
    # And the user's preferences will be turned off
    assert user_vetinari.main_notification_preferences.by_sms is False
