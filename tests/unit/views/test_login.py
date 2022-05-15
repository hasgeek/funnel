from werkzeug.datastructures import MultiDict

import pytest

from coaster.auth import current_auth
from funnel.models import User

fullname = 'wheatwater'
password = 'f7kN{$a58p^AmL@$'  # noqa: S105
email = 'wheatwater@gmail.com'


@pytest.fixture
def user_wheatwater(db_session):
    user = User(fullname=fullname, password=password)
    db_session.add(user)
    user.add_email(email)
    db_session.commit()
    yield user


def test_user_register(client):
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    rv = client.post(
        '/account/register',
        data=MultiDict(
            {
                'csrf_token': csrf_token,
                'fullname': fullname,
                'email': email,
                'password': password,
                'confirm_password': password,
            }
        ),
    )

    assert rv.status_code == 303
    assert current_auth.user.fullname == 'wheatwater'


def test_user_logout(client, user_wheatwater, login):
    login.as_(user_wheatwater)
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    rv = client.post('/account/logout', data={'csrf_token': csrf_token})

    assert rv.status_code == 200
    assert current_auth.user is None


def test_user_login_correct_password(client, user_wheatwater):
    csrf_token = client.get('/api/baseframe/1/csrf/refresh').get_data(as_text=True)
    rv = client.post(
        '/login',
        data=MultiDict(
            {
                'username': email,
                'password': password,
                'csrf_token': csrf_token,
                'form.id': 'passwordlogin',
            }
        ),
    )

    assert rv.status_code == 303
    assert current_auth.user.fullname == 'wheatwater'
