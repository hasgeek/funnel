"""Tests for support API views."""
# pylint: disable=redefined-outer-name

from __future__ import annotations

import secrets

from flask import Flask, url_for
from flask.testing import FlaskClient
import pytest

from funnel import models

VALID_PHONE = '+918123456789'
VALID_PHONE_UNPREFIXED = '8123456789'
VALID_PHONE_ZEROPREFIXED = '08123456789'
VALID_PHONE_INTL = '+12015550123'
VALID_PHONE_INTL_ZEROPREFIXED = '0012015550123'


@pytest.fixture()
def user_twoflower_phone(user_twoflower: models.User) -> models.AccountPhone:
    """User phone fixture."""
    return user_twoflower.add_phone(VALID_PHONE_INTL)


@pytest.fixture()
def user_rincewind_phone(user_rincewind: models.User) -> models.AccountPhone:
    """User phone fixture."""
    return user_rincewind.add_phone(VALID_PHONE)


@pytest.fixture()
def unaffiliated_phone_number() -> models.PhoneNumber:
    """Phone number not affiliated with a user account."""
    return models.PhoneNumber.add(VALID_PHONE)


@pytest.fixture()
def support_api_key(app: Flask) -> str:
    """Random support API key."""
    key = secrets.token_urlsafe()
    app.config['INTERNAL_SUPPORT_API_KEY'] = key
    return key


def test_api_key_not_configured(app: Flask, client: FlaskClient) -> None:
    """Server must be configured with an API key."""
    app.config.pop('INTERNAL_SUPPORT_API_KEY', None)
    rv = client.post(url_for('support_callerid'), data={'number': VALID_PHONE})
    assert rv.status_code == 501


def test_api_key_mismatch(client: FlaskClient, support_api_key: str) -> None:
    """Client must supply the correct API key."""
    rv = client.post(
        url_for('support_callerid'),
        data={'number': VALID_PHONE},
        headers={'Authorization': 'Bearer nonsense-key'},
    )
    assert rv.status_code == 403


def test_valid_phone_unaffiliated(
    client: FlaskClient,
    support_api_key: str,
    unaffiliated_phone_number: models.PhoneNumber,
) -> None:
    """Test phone number not affiliated with a user account."""
    rv = client.post(
        url_for('support_callerid'),
        data={'number': VALID_PHONE},
        headers={'Authorization': f'Bearer {support_api_key}'},
    )
    assert rv.status_code == 200
    data = rv.json
    assert data['result']['number'] == VALID_PHONE
    assert 'account' not in data['result']


@pytest.mark.parametrize(
    'number', [VALID_PHONE, VALID_PHONE_UNPREFIXED, VALID_PHONE_ZEROPREFIXED]
)
def test_valid_phone_affiliated(
    client: FlaskClient,
    support_api_key: str,
    user_rincewind_phone: models.AccountPhone,
    number: str,
) -> None:
    """Test phone number affiliated with a user account."""
    rv = client.post(
        url_for('support_callerid'),
        data={'number': number},
        headers={'Authorization': f'Bearer {support_api_key}'},
    )
    assert rv.status_code == 200
    data = rv.json
    assert data['result']['number'] == VALID_PHONE
    assert data['result']['account'] == {
        'title': user_rincewind_phone.user.fullname,
        'name': user_rincewind_phone.user.username,
    }


@pytest.mark.parametrize('number', [VALID_PHONE_INTL, VALID_PHONE_INTL_ZEROPREFIXED])
def test_valid_phone_intl(
    client: FlaskClient,
    support_api_key: str,
    user_twoflower_phone: models.AccountPhone,
    number: str,
) -> None:
    """Test phone number affiliated with a user account."""
    rv = client.post(
        url_for('support_callerid'),
        data={'number': number},
        headers={'Authorization': f'Bearer {support_api_key}'},
    )
    assert rv.status_code == 200
    data = rv.json
    assert data['result']['number'] == VALID_PHONE_INTL
    assert data['result']['account'] == {
        'title': user_twoflower_phone.user.fullname,
        'name': user_twoflower_phone.user.username,
    }
