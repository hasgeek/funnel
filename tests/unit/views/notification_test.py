"""Test Notification views."""
# pylint: disable=redefined-outer-name

from types import SimpleNamespace
from typing import cast
from urllib.parse import urlsplit

import pytest
from flask import url_for

from funnel import models
from funnel.transports.sms import SmsTemplate
from funnel.views.notifications.mixins import TemplateVarMixin


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
        created_by=user_vetinari,
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


def test_template_var_mixin() -> None:
    """Test TemplateVarMixin for common variables."""
    assert TemplateVarMixin.actor.name != TemplateVarMixin.user.name
    t1 = TemplateVarMixin()
    t1.var_max_length = 40

    p1 = SimpleNamespace(
        title='Ankh-Morpork 2010', joined_title='Ankh-Morpork / Ankh-Morpork 2010'
    )
    u1 = SimpleNamespace(
        pickername='Havelock Vetinari (@vetinari)', title='Havelock Vetinari'
    )
    u2 = SimpleNamespace(pickername='Twoflower', title='Twoflower')
    t1.project = cast(models.Project, p1)
    t1.user = cast(models.User, u2)
    t1.actor = cast(models.User, u1)
    assert isinstance(t1.project, str)
    assert isinstance(t1.actor, str)
    assert isinstance(t1.user, str)
    assert t1.project == 'Ankh-Morpork / Ankh-Morpork 2010'
    assert t1.actor == 'Havelock Vetinari (@vetinari)'
    assert t1.user == 'Twoflower'

    # Do this again to confirm truncation at a smaller size
    t1.var_max_length = 20
    t1.project = cast(models.Project, p1)
    t1.user = cast(models.User, u2)
    t1.actor = cast(models.User, u1)
    assert t1.project == 'Ankh-Morpork 2010'
    assert t1.actor == 'Havelock Vetinari'
    assert t1.user == 'Twoflower'

    # Again, even smaller
    t1.var_max_length = 15
    t1.project = cast(models.Project, p1)
    t1.user = cast(models.User, u2)
    t1.actor = cast(models.User, u1)
    assert t1.project == 'Ankh-Morpork 2…'
    assert t1.actor == 'Havelock Vetin…'
    assert t1.user == 'Twoflower'

    # Confirm deletion works
    del t1.project
    with pytest.raises(AttributeError):
        t1.project  # pylint: disable=pointless-statement
    with pytest.raises(AttributeError):
        del t1.project


class VarMessage(TemplateVarMixin, SmsTemplate):
    """Test case for TemplateVarMixin."""

    registered_template = '{#var#} shared {#var#} with {#var#}: {#var#}'
    template = "{actor} shared {project} with {user}: {url}"
    plaintext_template = template

    url: str


def test_template_var_mixin_in_template(
    project_expo2010: models.Project,
    user_vetinari: models.User,
    user_twoflower: models.User,
) -> None:
    """Confirm TemplateVarMixin performs interpolations correctly."""
    assert VarMessage.project is not None
    assert VarMessage.project.__set__ is not None
    msg = VarMessage(
        project=project_expo2010,
        actor=user_vetinari,
        user=user_twoflower,
        url=project_expo2010.url_for(_external=False),
    )
    assert msg.project == 'Ankh-Morpork 2010'
    assert msg.actor == 'Havelock Vetinari (@vetinari)'
    assert msg.user == 'Twoflower'
    assert msg.url == '/ankh_morpork/2010/'
    assert msg.vars().keys() == {'url'}  # Only 'url' was processed by SmsTemplate
    assert (
        str(msg)
        == 'Havelock Vetinari (@vetinari) shared Ankh-Morpork 2010 with Twoflower:'
        ' /ankh_morpork/2010/'
    )
