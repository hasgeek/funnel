"""Test account views."""

from types import SimpleNamespace
from typing import cast

import pytest

from funnel import models
from funnel.views.account import user_agent_details

from ...conftest import TestClient


def test_account_always_has_profile_url(
    user_twoflower: models.User, user_rincewind: models.User
) -> None:
    """An account without a username will still have an absolute URL for a profile."""
    assert user_twoflower.username is None
    assert user_twoflower.absolute_url is not None
    assert user_rincewind.username is not None
    assert user_rincewind.absolute_url is not None


def test_username_available(
    client: TestClient,
    user_rincewind: models.User,
    csrf_token: str,
) -> None:
    """Test the username availability endpoint."""
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
        data={'username': 'should_be_available', 'csrf_token': csrf_token},
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

    # Mis-formatted usernames will render an explanatory error
    rv = client.post(
        endpoint,
        data={'username': 'this is invalid', 'csrf_token': csrf_token},
    )
    assert rv.status_code == 200  # Validation failures are not 400/422
    assert rv.get_json() == {
        'status': 'error',
        'error': 'validation_failure',
        'error_description': "Usernames can only have alphabets, numbers and"
        " underscores",
    }


@pytest.mark.parametrize(
    ('user_agent', 'output'),
    [
        (
            'Mozilla/5.0 (Linux; Android 12; LE2121) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/101.0.4951.48 Mobile Safari/537.36',
            {
                'browser': 'Chrome Mobile 101.0.4951',
                'os_device': 'OnePlus LE2121 (Android 12)',
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            {'browser': 'Chrome 104.0.0', 'os_device': 'macOS'},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
            {'browser': 'Chrome 91.0.4472', 'os_device': 'Windows 10'},
        ),
        (
            'Mozilla/5.0 (X11; CrOS x86_64 13904.97.0) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/91.0.4472.167 Safari/537.36',
            {'browser': 'Chrome 91.0.4472', 'os_device': 'Chrome OS 13904.97.0'},
        ),
        (
            'python-requests/2.2.1 CPython/3.4.3 Linux/3.13.0-121-generic',
            {'browser': 'Python Requests 2.2', 'os_device': 'Linux 3.13.0'},
        ),
        (
            'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko)'
            ' Chrome/92.0.4515.115 Mobile Safari/537.36',
            {'browser': 'Chrome Mobile 92.0.4515', 'os_device': 'Android 11'},
        ),
        (
            'Mozilla/5.0 (Android 10; Mobile; rv:92.0) Gecko/92.0 Firefox/92.0',
            {'browser': 'Firefox Mobile 92.0', 'os_device': 'Android 10'},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edg/104.0.1293.63',
            {'browser': 'Edge 104.0.1293', 'os_device': 'Windows 10'},
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edg/104.0.1293.63',
            {'browser': 'Edge 104.0.1293', 'os_device': 'macOS 12.5.1'},
        ),
        (
            'Mozilla/5.0 (Linux; Android 10; Pixel 3 XL) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36'
            ' EdgA/100.0.1185.50',
            {
                'browser': 'Edge Mobile 100.0.1185',
                'os_device': 'Google Pixel 3 XL (Android 10)',
            },
        ),
        (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_6_1 like Mac OS X)'
            ' AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0'
            ' EdgiOS/100.1185.50 Mobile/15E148 Safari/605.1.15',
            {
                'browser': 'Edge Mobile 100.1185.50',
                'os_device': 'Apple iPhone (iOS 15.6.1)',
            },
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Xbox; Xbox One)'
            ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
            ' Edge/44.18363.8131',
            {'browser': 'Edge 44.18363.8131', 'os_device': 'Windows 10'},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 OPR/90.0.4480.54',
            {'browser': 'Opera 90.0.4480', 'os_device': 'Windows 10'},
        ),
        (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'
            ' Chrome/104.0.0.0 Safari/537.36 OPR/90.0.4480.54',
            {'browser': 'Opera 90.0.4480', 'os_device': 'Linux'},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36'
            ' (KHTML, like Gecko) Chrome/104.0.0.0 YaBrowser/22.7.3 Yowser/2.5'
            ' Safari/537.36',
            {'browser': 'Yandex Browser 22.7.3', 'os_device': 'Windows 10'},
        ),
    ],
)
def test_user_agent_details(user_agent: str, output: dict) -> None:
    assert (
        user_agent_details(
            cast(models.LoginSession, SimpleNamespace(user_agent=user_agent))
        )
        == output
    )
