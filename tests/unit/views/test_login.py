from itertools import product

from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth

test_passwords = {'rincewind': 'rincewind-password'}
complex_test_password = 'f7kN{$a58p^AmL@$'  # noqa: S105
wrong_password = 'wrong_password'  # noqa: S105

logins = ['rincewind', 'rincewind@example.com', '+12345678901']
passwords_with_status = [
    {
        'password': complex_test_password,
        'status_code': 303,
        'auth': True,
    },
    {'password': wrong_password, 'status_code': 200, 'auth': False},
]

# sms_response = {
#     "SMSMessage": {
#         "Sid": "0f477d60517e6e6a0f6d9a7e9af8630e",
#         "AccountSid": "Exotel",
#         "From": "0XXXXXX4890/WEBDEV",
#         "To": "0XXXXX30240",
#         "DateCreated": "2017-03-03 14:14:20",
#         "DateUpdated": "2017-03-03 14:14:20",
#         "DateSent": 'null',
#         "Body": random_otp(),
#         "Direction": "outbound-api",
#         "Uri": "/v1/Accounts/Exotel/SMS/Messages/0f477d60517e6e6a0f6d9a7e9af8630e.json",
#         "ApiVersion": 'null',
#         "Price": 'null',
#         "Status": "queued",
#         "DetailedStatusCode": "21010",
#         "DetailedStatus": "PENDING_TO_OPERATOR",
#         "SmsUnits": 'null',
#     }
# }


@pytest.fixture
def user_rincewind_with_password(user_rincewind):
    user_rincewind.password = complex_test_password
    return user_rincewind


@pytest.fixture
def user_rincewind_phone(user_rincewind):
    return user_rincewind.add_phone('+12345678901')


@pytest.fixture
def user_rincewind_email(user_rincewind):
    return user_rincewind.add_email('rincewind@example.com')


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


def test_user_logout(client, login, user_rincewind, csrf_token):
    login.as_(user_rincewind)
    client.get('/')
    assert current_auth.user == user_rincewind
    rv = client.post('/account/logout', data={'csrf_token': csrf_token})

    assert rv.status_code == 200
    assert current_auth.user is None


@pytest.mark.parametrize(
    ['login_type', 'passwords_with_status'], product(logins, passwords_with_status)
)
def test_login_types(
    client,
    csrf_token,
    passwords_with_status,
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
                'password': passwords_with_status['password'],
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
            }
        ),
    )

    assert current_auth.is_authenticated is passwords_with_status['auth']
    assert rv.status_code == passwords_with_status['status_code']


# def mock_send(phone, message, callback):
#     for prefix, sender in senders_by_prefix:
#         return sender(phone, message, callback)

# def test_sms(client,)
