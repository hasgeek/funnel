"""Test account views."""


def test_username_available(test_client, test_db, new_user):
    """Test the username availability endpoint."""
    endpoint = '/api/1/account/username_available'

    # Does not support GET requests
    rv = test_client.get(endpoint)
    assert rv.status_code == 405

    # Requires a username to process
    rv = test_client.post(endpoint)
    assert rv.status_code == 422  # Incomplete forms are 422 Unprocessable Entity
    assert rv.get_json() == {'status': 'error', 'error': 'username_required'}

    # Valid usernames will return an ok response
    rv = test_client.post(endpoint, data={'username': 'should-be-available'})
    assert rv.status_code == 200
    assert rv.get_json() == {'status': 'ok'}

    # Taken usernames won't be available
    rv = test_client.post(endpoint, data={'username': new_user.username})
    assert rv.status_code == 200  # Validation failures are not 400/422
    assert rv.get_json() == {
        'status': 'error',
        'error': 'validation_failure',
        'error_description': "This username has been taken",
    }

    # Misformatted usernames will render an explanatory error
    rv = test_client.post(endpoint, data={'username': 'this is invalid'})
    assert rv.status_code == 200  # Validation failures are not 400/422
    assert rv.get_json() == {
        'status': 'error',
        'error': 'validation_failure',
        'error_description': "Usernames can only have alphabets, numbers and dashes"
        " (except at the ends)",
    }
