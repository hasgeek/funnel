"""Tests for the login, logout and register views."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from flask import redirect, request, session
from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth
from coaster.utils import utcnow

from funnel.registry import LoginCallbackError, LoginInitError, LoginProviderData
from funnel.transports import TransportConnectionError, TransportRecipientError
from funnel.views.otp import OtpSession

pytestmark = pytest.mark.filterwarnings(
    "ignore:Object of type <AccountPhone> not in session",
    "ignore:Object of type <AccountEmail> not in session",
)

# User fixture's details
RINCEWIND_USERNAME = 'rincewind'
RINCEWIND_PHONE = '+917676332020'
RINCEWIND_EMAIL = 'rincewind@example.com'
LOGIN_USERNAMES = [RINCEWIND_USERNAME, RINCEWIND_EMAIL, RINCEWIND_PHONE]

# Test credentials
COMPLEX_TEST_PASSWORD = 'f7kN{$a58p^AmL@$'  # nosec
WRONG_PASSWORD = 'wrong-password'  # nosec
BLANK_PASSWORD = ''  # nosec
WEAK_TEST_PASSWORD = 'password'  # nosec
TEST_OAUTH_TOKEN = 'test_oauth_token'  # nosec

# Functions to patch to capture OTPs
PATCH_SMS_SEND = 'funnel.transports.sms.send'
PATCH_SMS_OTP = 'funnel.views.otp.OtpSession.send_sms'
PATCH_SMS_OTP_LOGIN = 'funnel.views.otp.OtpSessionForLogin.send_sms'
PATCH_EMAIL_OTP_LOGIN = 'funnel.views.otp.OtpSessionForLogin.send_email'
PATCH_GET_USER_EXT_ID = 'funnel.views.login.get_user_extid'

# Login provider patches
PATCH_LOGINHUB_DO = 'funnel.loginproviders.github.GitHubProvider.do'
PATCH_LOGINHUB_CALLBACK = 'funnel.loginproviders.github.GitHubProvider.callback'


# This fixture needs session scope as login_registry doesn't take kindly to lost items
@pytest.fixture(scope='session')
def loginhub(funnel):
    """Fake login provider for tests."""
    funnel.registry.login_registry[
        'loginhub'
    ] = funnel.loginproviders.github.GitHubProvider(  # nosec
        'loginhub',
        "Login Hub",
        at_login=True,
        priority=False,
        icon='github',
        key='no-key',
        secret='no-secret',
    )
    yield funnel.registry.login_registry['loginhub']
    del funnel.registry.login_registry['loginhub']


@pytest.fixture()
def user_rincewind_with_password(user_rincewind):
    """User fixture with a password."""
    user_rincewind.password = COMPLEX_TEST_PASSWORD
    return user_rincewind


@pytest.fixture()
def user_rincewind_phone(db_session, user_rincewind):
    """User phone fixture."""
    accountphone = user_rincewind.add_phone(RINCEWIND_PHONE)
    db_session.add(accountphone)
    return accountphone


@pytest.fixture()
def user_rincewind_email(db_session, user_rincewind):
    """User email fixture."""
    accountemail = user_rincewind.add_email(RINCEWIND_EMAIL)
    db_session.add(accountemail)
    return accountemail


@pytest.fixture()
def user_rincewind_with_weak_password(user_rincewind):
    """User fixture with a weak password."""
    user_rincewind.password = WEAK_TEST_PASSWORD
    return user_rincewind


@pytest.fixture()
def mock_loginhub_do(loginhub):
    """Mock LoginHub login provider's do method."""
    with patch(
        PATCH_LOGINHUB_DO,
        return_value=redirect('/login/loginhub/callback'),
    ) as mock:
        yield mock


@pytest.fixture()
def mock_loginhub_callback(loginhub):
    """Mock LoginHub login provider's callback method."""
    with patch(
        PATCH_LOGINHUB_CALLBACK,
        return_value=LoginProviderData(
            email=RINCEWIND_EMAIL,
            userid='rincewind-loginhub',
            fullname='Rincewind',
            oauth_token=TEST_OAUTH_TOKEN,
        ),
    ) as mock:
        yield mock


def test_user_rincewind_has_username(user_rincewind) -> None:
    """Confirm user fixture has the username required for further tests."""
    assert user_rincewind.username == RINCEWIND_USERNAME


def test_user_register_otp_sms(client, csrf_token) -> None:
    """Providing an unknown phone number sends an OTP and registers an account."""
    with patch(PATCH_SMS_SEND, return_value=None) as mock:
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
        message = mock.call_args[1]['message']
        caught_otp = message.otp
    assert rv1.form('form-otp') is not None
    assert rv1.status_code == 200

    with client:
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


def test_user_register_otp_email(client, csrf_token) -> None:
    """Providing an unknown email address sends an OTP and registers an account."""
    with patch(PATCH_EMAIL_OTP_LOGIN, autospec=True) as mock:
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
        otp_session = mock.call_args[0][0]
        caught_otp = otp_session.otp
    assert rv1.form('form-otp') is not None
    assert rv1.status_code == 200

    with client:
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


def test_user_logout(client, csrf_token, login, user_rincewind) -> None:
    """Logout works as a POST request."""
    with client:
        login.as_(user_rincewind)
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
    client, csrf_token, login_username, password_status_auth
) -> None:
    """Test how the login view responds to correct, incorrect and missing password."""
    with client:
        with patch(PATCH_SMS_SEND, return_value=None):
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
def test_valid_otp_login_sms(
    client, csrf_token, user_rincewind, login_username
) -> None:
    """Test OTP login using username or phone number."""
    with client:
        with patch(PATCH_SMS_SEND, return_value=None) as mock:
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
            message = mock.call_args[1]['message']
            caught_otp = message.otp

        assert rv1.form('form-otp') is not None
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
def test_valid_otp_login_email(
    client, csrf_token, user_rincewind, login_username
) -> None:
    """Test OTP login using username or email address."""
    with client:
        with patch(PATCH_EMAIL_OTP_LOGIN, autospec=True) as mock:
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
            otp_session = mock.call_args[0][0]
            caught_otp = otp_session.otp

        assert rv1.form('form-otp') is not None
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
def test_invalid_otp_login(client, csrf_token, login_username) -> None:
    """Using an incorrect OTP causes a login failure."""
    with client:
        with patch(PATCH_SMS_OTP_LOGIN, return_value=None, autospec=True), patch(
            PATCH_EMAIL_OTP_LOGIN, return_value=None, autospec=True
        ):
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
        assert rv1.status_code == 200
        assert current_auth.user is None

        rv2 = client.post(
            '/login',
            data=MultiDict(
                {
                    'otp': 'invalid',
                    'csrf_token': csrf_token,
                    'form.id': 'login-otp',
                }
            ),
        )
        assert rv2.form('form-otp') is not None
        assert rv2.status_code == 200
        assert current_auth.user is None


def test_user_has_sudo(client, login, user_rincewind) -> None:
    """Test that user has sudo mode enabled immediately after login."""
    login.as_(user_rincewind)
    rv = client.get('/account/sudo')
    assert rv.status_code == 303


@pytest.mark.dbcommit()
def test_user_password_sudo_prompt(client, login, user_rincewind_with_password) -> None:
    """User with a password gets a sudo password prompt."""
    with client:
        login.as_(user_rincewind_with_password)
        client.get('/account')
        current_auth.session.sudo_enabled_at -= timedelta(minutes=25)
        rv = client.get('/account/sudo')
        assert rv.form('form-sudo-password') is not None


@pytest.mark.dbcommit()
@pytest.mark.usefixtures('user_rincewind_phone')
def test_user_otp_sudo_timedout(client, login, user_rincewind) -> None:
    """User without a password gets a sudo OTP prompt."""
    with client:
        login.as_(user_rincewind)
        client.get('/account')
        current_auth.session.sudo_enabled_at -= timedelta(minutes=25)
        with patch(PATCH_SMS_SEND, return_value=None):
            rv = client.get('/account/sudo')
        assert rv.form('form-sudo-otp') is not None


@pytest.mark.usefixtures('user_rincewind_email', 'user_rincewind_with_weak_password')
def test_weak_password(client, csrf_token) -> None:
    """User attempting to login with a weak password is asked to change it."""
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


@pytest.mark.usefixtures('user_rincewind_email')
def test_expired_password(client, csrf_token, user_rincewind_with_password) -> None:
    """User attempting to login with an expired password is asked to change it."""
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


@pytest.mark.usefixtures('user_rincewind_email')
def test_login_password_exception(client, csrf_token) -> None:
    """User logging in to an account without a password is asked to reset it."""
    with client:
        rv = client.post(
            '/login',
            data=MultiDict(
                {
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                    'username': RINCEWIND_EMAIL,
                    'password': 'this does not need to match',
                }
            ),
        )
        assert rv.status_code == 303
        assert rv.location == '/account/reset'
        assert RINCEWIND_EMAIL in session['temp_username']


@pytest.mark.usefixtures('user_rincewind_phone')
def test_sms_otp_not_sent(client, csrf_token) -> None:
    """When an OTP could not be sent, user is prompted to use a password."""
    with patch(
        PATCH_SMS_SEND,
        side_effect=TransportConnectionError,
        autospec=True,
    ):
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

    assert "Unable to send an OTP to your phone number" in rv1.data.decode()
    assert "Use password to login" in rv1.data.decode()


@pytest.mark.usefixtures('user_rincewind_phone')
def test_otp_timeout_error(client, csrf_token) -> None:
    """When an OTP has expired, the user is prompted to try again."""
    with client:
        with patch(PATCH_SMS_OTP_LOGIN, return_value=None, autospec=True) as mock:
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
            otp_session = mock.call_args[0][0]
            caught_otp = otp_session.otp

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
        assert rv2.data.decode('utf-8').find("The OTP has expired. Try again?") != -1


@pytest.mark.usefixtures('user_rincewind_phone')
def test_otp_reason_error(client, csrf_token) -> None:
    """When an OTP is used for an incorrect reason, it is rejected with a 403."""
    with patch(PATCH_SMS_OTP, return_value=True, autospec=True) as mock:
        client.post(
            '/account/reset',
            data=MultiDict(
                {
                    'username': RINCEWIND_PHONE,
                    'csrf_token': csrf_token,
                }
            ),
        )
        otp_session = mock.call_args[0][0]
        caught_otp = otp_session.otp

    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'otp': caught_otp,
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
            }
        ),
    )
    assert rv.status_code == 403


@pytest.mark.usefixtures('mock_loginhub_do', 'mock_loginhub_callback')
def test_login_external(client) -> None:
    """External login flow works under mocked conditions."""
    rv = client.get('/login/loginhub')
    assert rv.status_code == 302
    assert rv.location == '/login/loginhub/callback'
    with client:
        rv = client.get(rv.location, follow_redirects=True)
        if rv.metarefresh is not None:
            rv = client.get(rv.metarefresh.url)
        assert current_auth.user is not None
        assert current_auth.user.fullname == 'Rincewind'
        assert current_auth.cookie != {}
        # User is logged in and is now being sent off to either index or /account/edit
        assert rv.status_code == 303
        client.get(rv.location)
        assert request.path in ('/', '/account/edit')
        assert current_auth.user is not None
        assert current_auth.user.fullname == 'Rincewind'


def test_service_not_in_registry(client) -> None:
    """Attempting to use an unknown external login causes a 404."""
    assert client.get('/login/unknown').status_code == 404
    assert client.get('/login/unknown/callback').status_code == 404


@pytest.mark.skip(reason="Test is incomplete")
def test_logout_using_client_id(client, login, user_twoflower) -> None:
    """Logout works using a valid client id and HTTP referrer."""
    login.as_(user_twoflower)
    rv1 = client.get('/logout?client_id=twoflower')

    assert '_flashes' in session
    assert rv1.status_code == 303

    rv2 = client.get('/logout?next=twoflower.com')
    assert '_flashes' in session
    assert rv2.status_code == 303


def test_already_logged_in(client, login, user_rincewind) -> None:
    """Login endpoint sends user away if they are already logged in."""
    login.as_(user_rincewind)
    rv = client.get('/login')
    assert rv.status_code == 303


@pytest.mark.usefixtures('user_rincewind_phone')
@pytest.mark.parametrize(
    ('phone_number', 'message_fragment'),
    [
        (RINCEWIND_PHONE, 'Use password to login'),
        ('+919845012345', 'Use an email address to register'),
    ],
)
def test_phone_otp_not_supported(
    client, csrf_token, phone_number, message_fragment
) -> None:
    """If phone number is an unsupported recipient, they are asked to try email."""
    with patch(
        PATCH_SMS_SEND,
        side_effect=TransportRecipientError,
        autospec=True,
    ):
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': phone_number,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        assert rv1.status_code == 200
        assert rv1.form('form-passwordlogin') is not None
        assert 'not supported for SMS' in rv1.data.decode()
        assert message_fragment in rv1.data.decode()


@pytest.mark.usefixtures('user_rincewind_phone')
@pytest.mark.parametrize(
    ('phone_number', 'message_fragment'),
    [
        (RINCEWIND_PHONE, 'Use password to login, or try again later'),
        ('+919845012345', 'Use an email address to register, or try again later'),
    ],
)
def test_phone_otp_not_sent(client, csrf_token, phone_number, message_fragment) -> None:
    """If OTP cannot be sent to phone, they are asked to try password/email."""
    with patch(
        PATCH_SMS_SEND,
        side_effect=TransportConnectionError,
        autospec=True,
    ):
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': phone_number,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        assert rv1.status_code == 200
        assert rv1.form('form-passwordlogin') is not None
        assert 'Unable to send an OTP to your phone number' in rv1.data.decode()
        assert message_fragment in rv1.data.decode()


@pytest.mark.usefixtures('user_rincewind_email', 'user_rincewind_with_weak_password')
def test_weak_password_exception(forms, client, csrf_token) -> None:
    """If login form blocks weak password, login view will force user to reset it."""
    with client:
        with patch(
            'funnel.forms.login.LoginForm.validate_password',
            side_effect=forms.LoginPasswordWeakException,
            autospec=True,
        ):
            rv = client.post(
                '/login',
                data=MultiDict(
                    {
                        'csrf_token': csrf_token,
                        'username': RINCEWIND_EMAIL,
                        'form.id': 'passwordlogin',
                        'password': WEAK_TEST_PASSWORD,
                    }
                ),
            )
        assert rv.status_code == 303
        assert rv.location == '/account/reset'
        assert 'request an OTP and set a new password' in str(session['_flashes'])


@pytest.mark.usefixtures('user_rincewind_email')
def test_incomplete_form(client, csrf_token) -> None:
    """A login form without form.id is rejected."""
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'username': RINCEWIND_EMAIL,
                'password': WEAK_TEST_PASSWORD,
            }
        ),
    )
    assert rv.status_code == 422


def test_render_login_form(client) -> None:
    """Login in an embedded view renders a HTML fragment."""
    rv = client.get(
        '/login',
        headers={'X-Requested-With': 'XmlHttpRequest'},
        data={'form.id': 'passwordlogin'},
    )
    assert rv.form('form-passwordlogin') is not None
    assert not rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


def test_logout_redirect_index(client) -> None:
    """GET request to legacy /logout is rejected."""
    rv = client.get('/logout')
    assert rv.status_code == 303
    assert rv.location == '/'


def test_account_logout_user_session(client, csrf_token, login, user_rincewind) -> None:
    """POST to logout with a session id removes that session in the background."""
    with client:
        login.as_(user_rincewind)
        rv = client.post(
            '/account/logout',
            data={'sessionid': current_auth.session.buid, 'csrf_token': csrf_token},
        )
        assert rv.status_code == 303
        assert rv.location == '/account'


def test_account_logout_user_session_json(
    client, csrf_token, login, user_rincewind
) -> None:
    """POST to logout can return a JSON confirmation."""
    with client:
        login.as_(user_rincewind)
        rv = client.post(
            '/account/logout',
            data={'sessionid': current_auth.session.buid, 'csrf_token': csrf_token},
            headers={'Accept': 'application/json'},
        )
        assert rv.json['status'] == 'ok'
        assert rv.status_code == 200


def test_account_logout_csrf_validation_json(client, login, user_rincewind) -> None:
    """Logout needs a CSRF token to prevent CSRF logout (JSON response)."""
    login.as_(user_rincewind)

    rv = client.post(
        '/account/logout',
        headers={'Accept': 'application/json'},
    )
    assert rv.json['status'] == 'error'
    assert rv.json['errors'] == {'csrf_token': ['The CSRF token is missing.']}


def test_account_logout_csrf_validation_html(client, login, user_rincewind) -> None:
    """Logout needs a CSRF token to prevent CSRF logout (HTML response)."""
    with client:
        login.as_(user_rincewind)

        rv = client.post(
            '/account/logout',
        )
        assert rv.status_code == 303
        assert rv.location == '/account'
        assert 'The CSRF token is missing.' in str(session['_flashes'])


def test_login_service_init_error(client) -> None:
    """If a login service raises an init error, the login attempt is aborted."""
    with client:
        with patch(
            PATCH_LOGINHUB_DO,
            side_effect=LoginInitError,
        ):
            rv = client.get('/login/loginhub')
        assert 'danger' in str(session['_flashes'])
        assert rv.status_code == 303
        assert rv.location == '/'


def test_login_service_callback_error(client) -> None:
    """If a login service raises a callback error, the login attempt is aborted."""
    with patch(
        PATCH_LOGINHUB_CALLBACK,
        side_effect=LoginCallbackError,
    ):
        rv = client.get('/login/loginhub/callback', follow_redirects=True)
        if rv.metarefresh is not None:
            rv = client.get(rv.metarefresh.url, follow_redirects=True)
    assert 'Login Hub login failed' in rv.data.decode()


def test_login_service_callback_is_authenticated(client, login, user_rincewind) -> None:
    """A callback error when logged in is handled."""
    login.as_(user_rincewind)

    with patch(
        PATCH_LOGINHUB_CALLBACK,
        side_effect=LoginCallbackError,
    ):
        rv = client.get('/login/loginhub/callback', follow_redirects=True)
        if rv.metarefresh is not None:
            rv = client.get(rv.metarefresh.url, follow_redirects=True)
    assert 'Login Hub login failed' in rv.data.decode()


@pytest.mark.usefixtures(
    'user_rincewind', 'user_rincewind_email', 'mock_loginhub_callback'
)
def test_account_merge(client, csrf_token, login, user_twoflower) -> None:
    """An external login service can trigger an account merger."""
    login.as_(user_twoflower)

    with client:
        rv = client.get('/login/loginhub/callback')
        if rv.status_code == 302:
            rv = client.get(rv.location)
        assert 'merge_buid' in session
        # Response may contain a meta-refresh redirect, so we don't test status_code or
        # location header here

        rv2 = client.get('/account/merge')
        assert rv2.form('form-mergeaccounts') is not None

        rv3 = client.post('/account/merge', data={'csrf_token': csrf_token})
        assert rv3.status_code == 303
        assert current_auth.user.fullname == 'Twoflower'
        assert 'merge_buid' not in session


def test_merge_buid_not_in_session(client, login, user_twoflower) -> None:
    """Account merger endpoint will fail when no merger is in progress."""
    with client:
        login.as_(user_twoflower)

        rv = client.get('/account/merge')
        assert 'merge_buid' not in session
        assert rv.status_code == 303
        assert rv.location == '/'
