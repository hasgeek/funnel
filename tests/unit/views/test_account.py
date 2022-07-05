"""Test account views."""


def test_username_available(db_session, client, user_rincewind, csrf_token):
    """Test the username availability endpoint."""
    db_session.commit()
    endpoint = '/api/1/account/username_available'

    # Does not support GET requests
    rv = client.get(endpoint)
    assert rv.status_code == 405

    # Requires a username to process
    rv = client.post(endpoint, data={'csrf_token': csrf_token})
    assert rv.status_code == 422  # Incomplete forms are 422 Unprocessable Entity
    assert rv.get_json() == {'status': 'error', 'error': 'username_required'}

    # Valid usernames will return an ok response
    rv = client.post(
        endpoint,
        data={'username': 'should-be-available', 'csrf_token': csrf_token},
    )
    assert rv.status_code == 200
    assert rv.get_json() == {'status': 'ok'}

    # Taken usernames won't be available
    rv = client.post(
        endpoint,
        data={'username': user_rincewind.username, 'csrf_token': csrf_token},
    )
    assert rv.status_code == 200  # Validation failures are not 400/422
    assert rv.get_json() == {
        'status': 'error',
        'error': 'validation_failure',
        'error_description': "This username has been taken",
    }

    # Misformatted usernames will render an explanatory error
    rv = client.post(
        endpoint,
        data={'username': 'this is invalid', 'csrf_token': csrf_token},
    )
    assert rv.status_code == 200  # Validation failures are not 400/422
    assert rv.get_json() == {
        'status': 'error',
        'error': 'validation_failure',
        'error_description': "Usernames can only have alphabets, numbers and dashes"
        " (except at the ends)",
    }


# Sample password that will pass zxcvbn's complexity validation, but will be flagged
# by the pwned password validator
PWNED_PASSWORD = "thisisone1"  # noqa: S105 #nosec


def test_pwned_password(client, csrf_token, login, user_rincewind):
    """Pwned password validator will block attempt to use a compromised password."""
    login.as_(user_rincewind)
    client.get('/')
    rv = client.post(
        'account/password',
        data={
            'username': user_rincewind.username,
            'form.id': 'password-change',
            'password': PWNED_PASSWORD,
            'confirm_password': PWNED_PASSWORD,
            'csrf_token': csrf_token,
        },
    )
    assert "This password was found in breached password lists" in rv.data.decode()


def test_pwned_password_mock_endpoint_down(
    requests_mock, client, csrf_token, login, user_rincewind
):
    """If the pwned password API is not available, the password is allowed."""
    requests_mock.get('https://api.pwnedpasswords.com/range/1F074', status_code=404)
    login.as_(user_rincewind)
    client.get('/')

    rv = client.post(
        'account/password',
        data={
            'username': user_rincewind.username,
            'form.id': 'password-change',
            'password': PWNED_PASSWORD,
            'confirm_password': PWNED_PASSWORD,
            'csrf_token': csrf_token,
        },
    )

    assert rv.status_code == 303
    assert rv.location == '/account'
