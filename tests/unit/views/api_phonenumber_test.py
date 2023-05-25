"""Test Phonenumber API views."""
# pylint: disable=redefined-outer-name

import pytest


@pytest.fixture()
def user_rincewind_phone(db_session, user_rincewind):
    """User phone fixture."""
    up = user_rincewind.add_phone("+917676332020")
    db_session.add(up)
    return up


def test_valid_phone_number(app, client, user_rincewind_phone) -> None:
    rv = client.post(
        '/api/1/support/callerid',
        data={'phone_number': '+917676332020'},
        headers={'x-api-key': 'abcdefgh'},
    )
    assert rv.status_code == 200
    assert rv.json['fullname'] == 'Rincewind'
    assert rv.json['username'] == 'rincewind'


def test_invalid_phone_number(app, client, user_rincewind_phone) -> None:
    rv = client.post(
        '/api/1/support/callerid',
        data={'phone_number': '+919123456789'},
        headers={'x-api-key': 'abcdefgh'},
    )
    assert rv.status_code == 404
    assert rv.json['error'] == 'user_not_found'


def test_invalid_api_key(app, client, user_rincewind_phone) -> None:
    rv = client.post(
        '/api/1/support/callerid',
        data={'phone_number': '+917676332020'},
        headers={'x-api-key': 'wrongkey'},
    )
    assert rv.status_code == 401
    assert rv.json['error'] == 'invalid_api_key'
