from itertools import product
from unittest.mock import patch
import json

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


def mock_send(phone, message):
    return json.dumps(sms_response)


@pytest.fixture
def user_rincewind_with_password(user_rincewind):
    user_rincewind.password = complex_test_password
    return user_rincewind


@pytest.fixture
def user_rincewind_phone(db_session, user_rincewind):
    up = user_rincewind.add_phone('+12345678901')
    db_session.add(up)
    return up


@pytest.fixture
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


@patch('funnel.transports.sms.send', mock_send)
@pytest.mark.parametrize('register_type', register_types)
def test_user_register_otp(client, csrf_token, register_type):
    rv1 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
                'username': register_type,
                'password': '',
            }
        ),
    )
    otp = retrieve_otp_session('login').otp
    assert rv1.forms[0]._name() == '#form-otp'
    assert rv1.status_code == 200

    rv2 = client.post(
        '/login',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'form.id': 'login-otp',
                'fullname': 'Test User',
                'otp': otp,
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


@patch('funnel.transports.sms.send', mock_send)
@pytest.mark.parametrize(
    ['login_type', 'password_with_status'],
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
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'username': str(login_type),
                'password': password_with_status['password'],
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
            }
        ),
    )
    assert current_auth.is_authenticated is password_with_status['auth']
    assert rv.status_code == password_with_status['status_code']


@patch('funnel.transports.sms.send', mock_send)
@pytest.mark.parametrize('login_type', logins)
def test_valid_otp_login(  # pylint: disable=too-many-arguments
    client,
    user_rincewind,
    user_rincewind_phone,
    user_rincewind_email,
    csrf_token,
    login_type,
):
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
                'otp': retrieve_otp_session('login').otp,
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


@patch('funnel.transports.sms.send', mock_send)
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
