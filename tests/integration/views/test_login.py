"""Tests for the login, logout and register views."""

from datetime import timedelta
from os import environ
from types import SimpleNamespace
from unittest.mock import patch

from flask import redirect, session
from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth
from coaster.utils import newpin, utcnow
from funnel.registry import LoginProviderData
from funnel.views.helpers import OtpSession

# User fixture's details
RINCEWIND_USERNAME = 'rincewind'
RINCEWIND_PHONE = '+12345678900'
RINCEWIND_EMAIL = 'rincewind@example.com'
LOGIN_USERNAMES = [RINCEWIND_USERNAME, RINCEWIND_EMAIL, RINCEWIND_PHONE]

COMPLEX_TEST_PASSWORD = 'f7kN{$a58p^AmL@$'  # nosec  # noqa: S105
WRONG_PASSWORD = 'wrong-password'  # nosec  # noqa: S105
BLANK_PASSWORD = ''  # nosec  # noqa: S105
WEAK_TEST_PASSWORD = 'password'  # nosec  # noqa: S105

# Functions to patch to capture OTPs
PATCH_SMS_OTP = 'funnel.transports.sms.send'
PATCH_SEND_SMS = 'funnel.views.login.send_sms_otp'
PATCH_EMAIL_OTP = 'funnel.views.login.send_email_login_otp'
PATCH_GET_USER_EXT_ID = 'funnel.views.login.get_user_extid'

TEST_OAUTH_TOKEN = 'test_oauth_token'  # nosec  # noqa: S105


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


# test_weak_password, test_expired_password, test_otp_not_sent, test_otp_timeout


@pytest.fixture()
def user_rincewind_with_weak_password(db_session, user_rincewind):
    user_rincewind.password = WEAK_TEST_PASSWORD
    return user_rincewind


@pytest.fixture()
def do_mock():
    with patch(
        'funnel.loginproviders.github.GitHubProvider.do',
        return_value=redirect('login/github/callback'),
    ) as mock:
        yield mock


@pytest.fixture()
def callback_mock(user_twoflower):
    with patch(
        'funnel.loginproviders.github.GitHubProvider.callback',
        return_value=LoginProviderData(
            email=RINCEWIND_EMAIL,
            userid='twof',
            fullname='Twoflower',
            oauth_token=TEST_OAUTH_TOKEN,
        ),
    ) as mock:
        yield mock


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
    rv1 = client.get('/account/register')
    assert rv1.forms[1].attrib['id'] == 'form-password-change'

    rv2 = client.post(
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

    assert rv2.status_code == 303
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
@pytest.mark.parametrize('login_username', LOGIN_USERNAMES)
@pytest.mark.parametrize(
    'password_status_auth',
    [
        SimpleNamespace(password=COMPLEX_TEST_PASSWORD, status_code=303, auth=True),
        SimpleNamespace(password=WRONG_PASSWORD, status_code=200, auth=False),
        # Blank password triggers OTP flow:
        SimpleNamespace(password=BLANK_PASSWORD, status_code=200, auth=False),
    ],
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
                'otp': generate_wrong_otp(OtpSession.retrieve('login').otp),
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv2.forms[0].attrib['id'] == 'form-otp'
    assert rv2.status_code == 200
    assert current_auth.user is None


def test_user_has_sudo(user_rincewind, login, client):
    login.as_(user_rincewind)
    client.get('/')
    rv = client.get('/account/sudo')
    assert rv.status_code == 303


def test_user_password_sudo_timedout(user_rincewind_with_password, login, client):
    login.as_(user_rincewind_with_password)
    client.get('account')
    current_auth.session.sudo_enabled_at -= timedelta(minutes=25)
    rv = client.get('/account/sudo')
    assert rv.forms[1].attrib['id'] == 'form-sudo-password'


def test_user_otp_sudo_timedout(user_rincewind, user_rincewind_phone, login, client):
    login.as_(user_rincewind)
    client.get('account')
    current_auth.session.sudo_enabled_at -= timedelta(minutes=25)
    with patch(PATCH_SMS_OTP, return_value=None):
        rv = client.get('/account/sudo')
    assert rv.forms[1].attrib['id'] == 'form-sudo-otp'


def test_weak_password(
    user_rincewind_email, user_rincewind_with_weak_password, client, csrf_token
):
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
                'username': RINCEWIND_EMAIL,
                'password': WEAK_TEST_PASSWORD,
            }
        ),
    )
    assert rv.status_code == 303
    assert '/account/password' in rv.location


def test_expired_password(
    user_rincewind,
    user_rincewind_email,
    user_rincewind_with_password,
    csrf_token,
    client,
    db_session,
):
    db_session.add(user_rincewind_with_password)
    db_session.commit()
    user_rincewind_with_password.pw_expires_at = utcnow()
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
                'username': RINCEWIND_EMAIL,
                'password': COMPLEX_TEST_PASSWORD,
            }
        ),
    )
    assert rv.status_code == 303
    assert '/account/password' in rv.location


def test_login_password_exception(
    user_rincewind,
    user_rincewind_email,
    csrf_token,
    client,
    login,
    db_session,
):
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
                'username': RINCEWIND_EMAIL,
                'password': WEAK_TEST_PASSWORD,
            }
        ),
    )
    assert rv.location == '/account/reset'
    assert RINCEWIND_EMAIL in session['temp_username']
    assert rv.status_code == 303


def test_sms_otp_not_sent(user_rincewind_phone, csrf_token, client):
    with patch(PATCH_SEND_SMS, return_value=None):
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': RINCEWIND_PHONE,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )

    assert (
        rv1.data.decode("utf-8").find(
            'The OTP could not be sent. Use password to login or try again'
        )
        != -1
    )


def test_otp_timeout_error(user_rincewind_phone, user_rincewind, csrf_token, client):
    with patch(PATCH_SEND_SMS, return_value=None) as mock:
        client.post(
            '/login',
            data=MultiDict(
                {
                    'username': RINCEWIND_PHONE,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']

    OtpSession.delete()

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
    assert rv2.status_code == 200
    assert current_auth.user is None
    assert rv2.data.decode("utf-8").find('The OTP has expired. Try again?') != -1


def test_otp_reason_error(user_rincewind_phone, user_rincewind, csrf_token, client):
    with patch(PATCH_SEND_SMS, return_value=None) as mock:
        client.post(
            '/login',
            data=MultiDict(
                {
                    'username': RINCEWIND_PHONE,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )

        client.post(
            '/account/reset',
            data=MultiDict(
                {
                    'username': RINCEWIND_PHONE,
                    'csrf_token': csrf_token,
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']

    rv3 = client.post(
        '/login',
        data=MultiDict(
            {
                'otp': caught_otp,
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv3.status_code == 403


@pytest.mark.skipif(environ.get('OAUTH_GITHUB_KEY') == '', reason='no test credentials')
def test_login_external(db_session, client, callback_mock, do_mock, user_twoflower):
    rv1 = client.get('/login/github')
    assert rv1.status_code == 302
    rv2 = client.get(rv1.location)
    assert rv2.status_code == 200
    assert current_auth.user.name == user_twoflower.name


@pytest.mark.skipif(environ.get('OAUTH_GITHUB_KEY') == '', reason='no test credentials')
def test_account_merge(
    user_twoflower,
    user_rincewind_email,
    user_rincewind,
    db_session,
    login,
    client,
    callback_mock,
    csrf_token,
):
    db_session.add(user_rincewind_email)
    db_session.commit()

    login.as_(user_twoflower)
    client.get('')

    client.get('login/github/callback')
    assert bool(session['merge_buid']) is True

    rv2 = client.get('account/merge')
    assert rv2.forms[1].attrib['id'] == 'form-mergeaccounts'

    rv3 = client.post('account/merge', data={'csrf_token': csrf_token})
    assert rv3.status_code == 303
    assert current_auth.user.fullname == 'Twoflower'
    assert 'merge_buid' not in session


def test_merge_buid_not_in_session(user_twoflower, login, client):
    login.as_(user_twoflower)
    client.get('')

    rv = client.get('account/merge')
    assert 'merge_buid' not in session
    assert rv.status_code == 303


# def test_service_not_in_registry(client):
#     rv1 = client.get('login/some_service')
#     rv2 = client.get('login/some_service/callback')
#     assert rv1.status_code == 404
#     assert rv2.status_code == 404


# def test_logout_using_client_id(client, user_twoflower, login):
#     login.as_(user_twoflower)
#     client.get('')
#     rv1 = client.get('/logout?client_id=twoflower')

#     assert '_flashes' in session
#     assert rv1.status_code == 303

#     rv2 = client.get('/logout?next=twoflower.com')
#     assert '_flashes' in session
#     assert rv2.status_code == 303
