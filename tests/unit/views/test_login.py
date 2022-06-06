"""Tests for the login, logout and register views."""

from itertools import product
from types import SimpleNamespace
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth
from coaster.utils import newpin
from funnel.views.helpers import retrieve_otp_session

# User fixture's details
RINCEWIND_USERNAME = 'rincewind'
RINCEWIND_PHONE = '+12345678901'
RINCEWIND_EMAIL = 'rincewind@example.com'
LOGIN_USERNAMES = [RINCEWIND_USERNAME, RINCEWIND_EMAIL, RINCEWIND_PHONE]

COMPLEX_TEST_PASSWORD = 'f7kN{$a58p^AmL@$'  # nosec  # noqa: S105
WRONG_PASSWORD = 'wrong-password'  # nosec  # noqa: S105
BLANK_PASSWORD = ''  # nosec  # noqa: S105

# Functions to patch to capture OTPs
PATCH_SMS_OTP = 'funnel.transports.sms.send'
PATCH_EMAIL_OTP = 'funnel.views.login.send_email_login_otp'


@pytest.fixture()
def user_rincewind_with_password(user_rincewind):
    """User fixture with a password."""
    user_rincewind.password = COMPLEX_TEST_PASSWORD
    return user_rincewind


@pytest.fixture()
def user_rincewind_phone(db_session, user_rincewind):
    """User phone fixture."""
    up = user_rincewind.add_phone(RINCEWIND_PHONE)
    db_session.add(up)
    return up


@pytest.fixture()
def user_rincewind_email(db_session, user_rincewind):
    """User email fixture."""
    ue = user_rincewind.add_email(RINCEWIND_EMAIL)
    db_session.add(ue)
    return ue


def generate_wrong_otp(correct_otp):
    """Generate a random OTP that does not match the reference correct OTP."""
    while True:
        wrong_otp = newpin()
        if wrong_otp != correct_otp:
            break
    return wrong_otp


def test_user_rincewind_has_username(user_rincewind):
    """Confirm user fixture has the username required for further tests."""
    assert user_rincewind.username == RINCEWIND_USERNAME


def test_user_register(client, csrf_token):
    """Register a user account using the legacy registration view."""
    rv = client.post(
        '/account/register',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'fullname': "Test User",
                'email': 'email@example.com',
                'password': COMPLEX_TEST_PASSWORD,
                'confirm_password': COMPLEX_TEST_PASSWORD,
            }
        ),
    )

    assert rv.status_code == 303
    assert current_auth.user.fullname == "Test User"


def test_user_register_otp_sms(client, csrf_token):
    """Providing an unknown phone number sends an OTP and registers an account."""
    with patch(PATCH_SMS_OTP, return_value=None) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                    'username': RINCEWIND_PHONE,
                    'password': '',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['message'].otp
    assert rv1.forms[0].attrib['id'] == 'form-otp'
    assert rv1.status_code == 200

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
                'fullname': "Rincewind",
                'otp': caught_otp,
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user.fullname == "Rincewind"


def test_user_register_otp_email(
    client,
    csrf_token,
):
    """Providing an unknown email address sends an OTP and registers an account."""
    with patch(PATCH_EMAIL_OTP) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                    'username': RINCEWIND_EMAIL,
                    'password': '',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']
    assert rv1.forms[0].attrib['id'] == 'form-otp'
    assert rv1.status_code == 200

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
                'fullname': "Rincewind",
                'otp': caught_otp,
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user.fullname == "Rincewind"
    assert str(current_auth.user.email) == RINCEWIND_EMAIL


def test_user_logout(client, login, user_rincewind, csrf_token):
    """Logout works as a POST request."""
    login.as_(user_rincewind)
    client.get('/')
    assert current_auth.user == user_rincewind
    rv = client.post('/account/logout', data={'csrf_token': csrf_token})

    assert rv.status_code == 200
    assert current_auth.user is None


@pytest.mark.usefixtures(
    'user_rincewind_with_password', 'user_rincewind_phone', 'user_rincewind_email'
)
@pytest.mark.parametrize(
    ('login_username', 'password_status_auth'),
    product(
        LOGIN_USERNAMES,
        [
            SimpleNamespace(password=COMPLEX_TEST_PASSWORD, status_code=303, auth=True),
            SimpleNamespace(password=WRONG_PASSWORD, status_code=200, auth=False),
            # Blank password triggers OTP flow:
            SimpleNamespace(password=BLANK_PASSWORD, status_code=200, auth=False),
        ],
    ),
)
def test_login_usernames(
    client,
    csrf_token,
    login_username,
    password_status_auth,
):
    """Test how the login view responds to correct, incorrect and missing password."""
    with patch(PATCH_SMS_OTP, return_value=None):
        rv = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': login_username,
                    'password': password_status_auth.password,
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
    assert current_auth.is_authenticated is password_status_auth.auth
    assert rv.status_code == password_status_auth.status_code


@pytest.mark.usefixtures('user_rincewind_phone')
@pytest.mark.parametrize('login_username', [RINCEWIND_USERNAME, RINCEWIND_PHONE])
def test_valid_otp_login_sms(client, csrf_token, user_rincewind, login_username):
    """Test OTP login using username or phone number."""
    with patch(PATCH_SMS_OTP, return_value=None) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': login_username,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['message'].otp

    assert rv1.forms[0].attrib['id'] == 'form-otp'
    assert rv1.status_code == 200
    assert current_auth.user is None

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'otp': caught_otp,
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user == user_rincewind


@pytest.mark.usefixtures('user_rincewind_email')
@pytest.mark.parametrize('login_username', [RINCEWIND_USERNAME, RINCEWIND_EMAIL])
def test_valid_otp_login_email(client, csrf_token, user_rincewind, login_username):
    """Test OTP login using username or email address."""
    with patch(PATCH_EMAIL_OTP) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': login_username,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']

    assert rv1.forms[0].attrib['id'] == 'form-otp'
    assert rv1.status_code == 200
    assert current_auth.user is None

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'otp': caught_otp,
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user == user_rincewind


@pytest.mark.usefixtures('user_rincewind_phone', 'user_rincewind_email')
@pytest.mark.parametrize('login_username', LOGIN_USERNAMES)
def test_invalid_otp_login(
    client,
    csrf_token,
    login_username,
):
    """Using an incorrect OTP causes a login failure."""
    with patch(PATCH_SMS_OTP, return_value=None):
        with patch(PATCH_EMAIL_OTP, return_value=None):
            rv1 = client.post(
                '/login',
                data=MultiDict(
                    {
                        'username': login_username,
                        'password': '',
                        'csrf_token': csrf_token,
                        'form.id': 'passwordlogin',
                    }
                ),
            )
    assert rv1.forms[0].attrib['id'] == 'form-otp'
    assert rv1.status_code == 200
    assert current_auth.user is None

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'otp': generate_wrong_otp(retrieve_otp_session('login').otp),
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv2.forms[0].attrib['id'] == 'form-otp'
    assert rv2.status_code == 200
    assert current_auth.user is None
