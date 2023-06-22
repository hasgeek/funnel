"""Tests to add a new phone number or email address."""
# pylint: disable=redefined-outer-name

from unittest.mock import patch

import pytest
from werkzeug.datastructures import MultiDict

from coaster.utils import newpin

from funnel import models

PATCH_EMAIL_VALIDATOR = (
    'funnel.models.email_address.EmailAddress.is_valid_email_address'
)
PATCH_SMS_OTP_SEND = 'funnel.views.otp.OtpSessionForNewPhone.send_sms'
PATCH_EMAIL_OTP_SEND = 'funnel.views.otp.OtpSessionForNewEmail.send_email'

TEST_NEW_EMAIL = 'rincewind@example.com'
TEST_NEW_PHONE = '+918123456789'


@pytest.fixture()
def useremail_rincewind(user_rincewind: models.User) -> models.UserEmail:
    """Email address for user fixture."""
    return user_rincewind.add_email(TEST_NEW_EMAIL)


@pytest.fixture()
def userphone_rincewind(user_rincewind: models.User) -> models.UserPhone:
    """Phone number for user fixture."""
    return user_rincewind.add_phone(TEST_NEW_PHONE)


def get_wrong_otp(reference: str) -> str:
    """Return a random value that does not match the reference value."""
    result = reference
    while result == reference:
        result = newpin(len(reference))
    return result


def test_add_email_wrong_otp(
    client, csrf_token, login, user_rincewind: models.User
) -> None:
    """Add a new email address with an OTP and confirm an incorrect OTP is rejected."""
    login.as_(user_rincewind)

    with patch(PATCH_EMAIL_VALIDATOR, return_value=True):
        with patch(PATCH_EMAIL_OTP_SEND, autospec=True, return_value=True) as mock:
            rv1 = client.post(
                '/account/email/new',
                data=MultiDict({'csrf_token': csrf_token, 'email': TEST_NEW_EMAIL}),
            )
            assert rv1.status_code == 303
            otp_session = mock.call_args[0][0]  # First call, first argument (self)
            caught_otp = otp_session.otp

        rv2 = client.post(
            rv1.location,
            data=MultiDict(
                {'csrf_token': csrf_token, 'otp': get_wrong_otp(caught_otp)}
            ),
        )
        assert 'OTP is incorrect' in rv2.data.decode()


def test_add_email(client, csrf_token, login, user_rincewind: models.User) -> None:
    """Add a new email address with an OTP."""
    login.as_(user_rincewind)
    assert user_rincewind.emails == []

    with patch(PATCH_EMAIL_VALIDATOR, return_value=True):
        with patch(PATCH_EMAIL_OTP_SEND, autospec=True, return_value=True) as mock:
            rv1 = client.post(
                '/account/email/new',
                data=MultiDict({'csrf_token': csrf_token, 'email': TEST_NEW_EMAIL}),
            )
            assert rv1.status_code == 303
            otp_session = mock.call_args[0][0]  # First call, first argument (self)
            caught_otp = otp_session.otp

        rv2 = client.post(
            rv1.location, data=MultiDict({'csrf_token': csrf_token, 'otp': caught_otp})
        )
        assert rv2.status_code == 303

    assert str(user_rincewind.email) == TEST_NEW_EMAIL


def test_merge_with_email_otp(
    client, csrf_token, login, useremail_rincewind, user_mort
) -> None:
    """Providing a valid OTP for another user's email address causes a merge prompt."""
    login.as_(user_mort)
    assert user_mort.emails == []
    with patch(PATCH_EMAIL_VALIDATOR, return_value=True):
        with patch(PATCH_EMAIL_OTP_SEND, autospec=True, return_value=True) as mock:
            rv1 = client.post(
                '/account/email/new',
                data=MultiDict({'csrf_token': csrf_token, 'email': TEST_NEW_EMAIL}),
            )
            assert rv1.status_code == 303
            otp_session = mock.call_args[0][0]  # First call, first argument (self)
            caught_otp = otp_session.otp

        rv2 = client.post(
            rv1.location, data=MultiDict({'csrf_token': csrf_token, 'otp': caught_otp})
        )
        assert rv2.status_code == 303
        assert user_mort.emails == []
        assert rv2.location == '/account/merge'
        with client.session_transaction() as session:
            assert session['merge_buid'] == useremail_rincewind.user.buid


def test_add_phone_wrong_otp(
    client, csrf_token, login, user_rincewind: models.User
) -> None:
    """Add a new phone number with an OTP and confirm an incorrect OTP is rejected."""
    login.as_(user_rincewind)

    assert user_rincewind.phones == []

    with patch(PATCH_SMS_OTP_SEND, autospec=True, return_value=True) as mock:
        rv1 = client.post(
            '/account/phone/new',
            data=MultiDict({'csrf_token': csrf_token, 'phone': TEST_NEW_PHONE}),
        )
        assert rv1.status_code == 303
        otp_session = mock.call_args[0][0]  # First call, first argument (self)
        caught_otp = otp_session.otp

    rv2 = client.post(
        rv1.location,
        data=MultiDict({'csrf_token': csrf_token, 'otp': get_wrong_otp(caught_otp)}),
    )
    assert 'OTP is incorrect' in rv2.data.decode()


def test_add_phone(client, csrf_token, login, user_rincewind: models.User) -> None:
    """Add a new phone number with an OTP."""
    login.as_(user_rincewind)
    assert user_rincewind.phones == []

    with patch(PATCH_SMS_OTP_SEND, autospec=True, return_value=True) as mock:
        rv1 = client.post(
            '/account/phone/new',
            data=MultiDict({'csrf_token': csrf_token, 'phone': TEST_NEW_PHONE}),
        )
        assert rv1.status_code == 303
        otp_session = mock.call_args[0][0]  # First call, first argument (self)
        caught_otp = otp_session.otp

    rv2 = client.post(
        rv1.location, data=MultiDict({'csrf_token': csrf_token, 'otp': caught_otp})
    )
    assert rv2.status_code == 303

    assert str(user_rincewind.phone) == TEST_NEW_PHONE


def test_merge_with_phone_otp(
    client, csrf_token, login, userphone_rincewind, user_mort
) -> None:
    """Providing a valid OTP for another user's phone number causes a merge prompt."""
    login.as_(user_mort)
    assert user_mort.phones == []
    with patch(PATCH_SMS_OTP_SEND, autospec=True, return_value=True) as mock:
        rv1 = client.post(
            '/account/phone/new',
            data=MultiDict({'csrf_token': csrf_token, 'phone': TEST_NEW_PHONE}),
        )
        assert rv1.status_code == 303
        assert rv1.location == '/account/phone/verify'
        otp_session = mock.call_args[0][0]  # First call, first argument (self)
        caught_otp = otp_session.otp

    rv2 = client.post(
        rv1.location, data=MultiDict({'csrf_token': csrf_token, 'otp': caught_otp})
    )
    assert rv2.status_code == 303
    assert user_mort.phones == []
    assert rv2.location == '/account/merge'
    with client.session_transaction() as session:
        assert session['merge_buid'] == userphone_rincewind.user.buid
