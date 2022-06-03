from itertools import product
from unittest.mock import patch

from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth
from coaster.utils import newpin
from funnel.views.helpers import retrieve_otp_session

test_passwords = {'rincewind': 'rincewind-password'}
complex_test_password = 'f7kN{$a58p^AmL@$'  # nosec  # noqa: S105

logins = ['rincewind', 'rincewind@example.com', '+12345678901']
register_types = ['example@example.com', '+12345678901']

sms_response = {
    "SMSMessage": {
        "Sid": "0f477d60517e6e6a0f6d9a7e9af8630e",
        "AccountSid": "Exotel",
        "From": "0XXXXXX4890/WEBDEV",
        "To": "0XXXXX30240",
        "DateCreated": "2017-03-03 14:14:20",
        "DateUpdated": "2017-03-03 14:14:20",
        "DateSent": 'null',
        "Body": '2234',
        "Direction": "outbound-api",
        "Uri": "/v1/Accounts/Exotel/SMS/Messages/0f477d60517e6e6a0f6d9a7e9af8630e.json",
        "ApiVersion": 'null',
        "Price": 'null',
        "Status": "queued",
        "DetailedStatusCode": "21010",
        "DetailedStatus": "PENDING_TO_OPERATOR",
        "SmsUnits": 'null',
    }
}


@pytest.fixture()
def user_rincewind_with_password(user_rincewind):
    user_rincewind.password = complex_test_password
    return user_rincewind


@pytest.fixture()
def user_rincewind_phone(db_session, user_rincewind):
    up = user_rincewind.add_phone('+12345678901')
    db_session.add(up)
    return up


@pytest.fixture()
def user_rincewind_email(db_session, user_rincewind):
    ue = user_rincewind.add_email('rincewind@example.com')
    db_session.add(ue)
    return ue


def test_user_register(client, csrf_token):
    rv = client.post(
        '/account/register',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'fullname': "Test User",
                'email': 'email@example.com',
                'password': complex_test_password,
                'confirm_password': complex_test_password,
            }
        ),
    )

    assert rv.status_code == 303
    assert current_auth.user.fullname == "Test User"


def test_user_register_otp_sms(client, csrf_token):
    caught_otp = None
    with patch('funnel.transports.sms.send', return_value=None) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                    'username': '+12345678901',
                    'password': '',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['message'].otp
    assert rv1.forms[0]._name() == '#form-otp'
    assert rv1.status_code == 200

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
                'fullname': 'Test User',
                'otp': caught_otp,
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user.fullname == "Test User"


def test_user_register_otp_email(
    client,
    csrf_token,
):
    caught_otp = None
    with patch('funnel.views.login.send_login_otp') as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                    'username': 'rincewind@example.com',
                    'password': '',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']
    assert rv1.forms[0]._name() == '#form-otp'
    assert rv1.status_code == 200

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
                'fullname': 'Test User',
                'otp': caught_otp,
            }
        ),
    )
    assert rv2.status_code == 303
    assert current_auth.user.fullname == "Test User"


def test_user_logout(client, login, user_rincewind, csrf_token):
    login.as_(user_rincewind)
    client.get('/')
    assert current_auth.user == user_rincewind
    rv = client.post('/account/logout', data={'csrf_token': csrf_token})

    assert rv.status_code == 200
    assert current_auth.user is None


@pytest.mark.parametrize(
    ('login_type', 'password_with_status'),
    product(
        logins,
        [
            {'password': complex_test_password, 'status_code': 303, 'auth': True},
            {'password': 'wrong-password', 'status_code': 200, 'auth': False},
            {'password': '', 'status_code': 200, 'auth': False},  # Trigger OTP login,
        ],
    ),
)
def test_login_types(  # pylint: disable=too-many-arguments
    client,
    csrf_token,
    password_with_status,
    login_type,
    user_rincewind,
    user_rincewind_with_password,
    user_rincewind_phone,
    user_rincewind_email,
):
    with patch('funnel.transports.sms.send', return_value=None):
        rv = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': str(login_type),
                    'password': passwords_with_status['password'],
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
    assert current_auth.is_authenticated is passwords_with_status['auth']
    assert rv.status_code == passwords_with_status['status_code']


@pytest.mark.parametrize('login_type', ['rincewind', '+12345678901'])
def test_valid_otp_login_sms(
    client,
    user_rincewind,
    user_rincewind_phone,
    user_rincewind_email,
    csrf_token,
    login_type,
):
    caught_otp = None
    with patch('funnel.transports.sms.send', return_value=None) as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': login_type,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['message'].otp

    assert rv1.forms[0]._name() == '#form-otp'
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


def test_valid_otp_login_email(
    client,
    user_rincewind,
    user_rincewind_email,
    csrf_token,
):
    caught_otp = None
    with patch('funnel.views.login.send_login_otp') as mock:
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': 'rincewind@example.com',
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
        caught_otp = mock.call_args.kwargs['otp']

    assert rv1.forms[0]._name() == '#form-otp'
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


def generate_wrong_otp(retrieved_otp):
    while True:
        wrong_otp = newpin()
        if wrong_otp != retrieved_otp:
            break
    return wrong_otp


@pytest.mark.parametrize('login_type', logins)
def test_invalid_otp_login(  # pylint: disable=too-many-arguments
    client,
    user_rincewind,
    user_rincewind_email,
    user_rincewind_phone,
    csrf_token,
    login_type,
    db_session,
):
    with patch('funnel.transports.sms.send', return_value=None):
        rv1 = client.post(
            '/login',
            data=MultiDict(
                {
                    'username': login_type,
                    'password': '',
                    'csrf_token': csrf_token,
                    'form.id': 'passwordlogin',
                }
            ),
        )
    assert rv1.forms[0]._name() == '#form-otp'
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
    assert rv2.forms[0]._name() == '#form-otp'
    assert rv2.status_code == 200
    assert current_auth.user is None
