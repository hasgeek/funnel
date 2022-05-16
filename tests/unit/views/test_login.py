from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth

test_passwords = {'rincewind': 'rincewind-password'}

complex_test_password = 'f7kN{$a58p^AmL@$'  # noqa: S105


@pytest.fixture
def user_rincewind_with_password(user_rincewind):
    user_rincewind.password = test_passwords['rincewind']
    return user_rincewind


@pytest.fixture
def user_rincewind_phone(user_rincewind):
    return user_rincewind.add_phone('+12345678901')


@pytest.fixture
def user_rincewind_email(user_rincewind):
    return user_rincewind.add_email('rincewind@example.com')


def test_user_register(client):
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
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


def test_user_logout(client, login, user_rincewind):
    login.as_(user_rincewind)
    assert current_auth.user == user_rincewind
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    rv = client.post('/account/logout', data={'csrf_token': csrf_token})

    assert rv.status_code == 200
    assert current_auth.user is None


def test_user_login_correct_password(client, user_rincewind, user_rincewind_email):
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'username': str(user_rincewind_email),
                'password': test_passwords['rincewind'],
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
            }
        ),
    )

    assert rv.status_code == 303
    assert current_auth.user == user_rincewind
