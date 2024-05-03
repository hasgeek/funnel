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
        'error_description': "This username is taken",
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
    ('user_agent', 'client_hints', 'output'),
    [
        (
            'Mozilla/5.0 (Linux; Android 12; LE2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.48 Mobile Safari/537.36',
            None,
            {
                'browser': 'Chrome Mobile 101.0.4951',
                'device_platform': 'OnePlus LE2121 (Android 12)',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            None,
            {'browser': 'Chrome 104.0.0', 'device_platform': 'macOS', 'mobile': False},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36',
            None,
            {
                'browser': 'Chrome 91.0.4472',
                'device_platform': 'Windows',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (X11; CrOS x86_64 13904.97.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.167 Safari/537.36',
            None,
            {
                'browser': 'Chrome 91.0.4472',
                'device_platform': 'Chrome OS 13904.97.0',
                'mobile': False,
            },
        ),
        (
            'python-requests/2.2.1 CPython/3.4.3 Linux/3.13.0-121-generic',
            None,
            {
                'browser': 'Python Requests 2.2',
                'device_platform': 'Linux 3.13.0',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.115 Mobile Safari/537.36',
            None,
            {
                'browser': 'Chrome Mobile 92.0.4515',
                'device_platform': 'Android 11',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Android 10; Mobile; rv:92.0) Gecko/92.0 Firefox/92.0',
            None,
            {
                'browser': 'Firefox Mobile 92.0',
                'device_platform': 'Android',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edg/104.0.1293.63',
            None,
            {
                'browser': 'Edge 104.0.1293',
                'device_platform': 'Windows',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edg/104.0.1293.63',
            None,
            {
                'browser': 'Edge 104.0.1293',
                'device_platform': 'macOS 12.5.1',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Linux; Android 10; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.97 Mobile Safari/537.36 EdgA/100.0.1185.50',
            None,
            {
                'browser': 'Edge Mobile 100.0.1185',
                'device_platform': 'Google Pixel 3 XL (Android)',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 EdgiOS/100.1185.50 Mobile/15E148 Safari/605.1.15',
            None,
            {
                'browser': 'Edge Mobile 100.1185.50',
                'device_platform': 'Apple iPhone (iOS 15.6.1)',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; Xbox; Xbox One) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 Edge/44.18363.8131',
            None,
            {
                'browser': 'Edge 44.18363.8131',
                'device_platform': 'Windows',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 OPR/90.0.4480.54',
            None,
            {
                'browser': 'Opera 90.0.4480',
                'device_platform': 'Windows',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36 OPR/90.0.4480.54',
            None,
            {'browser': 'Opera 90.0.4480', 'device_platform': 'Linux', 'mobile': False},
        ),
        (
            'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 YaBrowser/22.7.3 Yowser/2.5 Safari/537.36',
            None,
            {
                'browser': 'Yandex Browser 22.7.3',
                'device_platform': 'Windows',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
            None,
            {
                'browser': 'Chrome Mobile 124.0.0',
                'device_platform': 'Android',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            {
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-ch-ua-platform-version': '"14.4.1"',
                'sec-ch-ua-full-version-list': '"Chromium";v="124.0.6367.118", "Google Chrome";v="124.0.6367.118", "Not-A.Brand";v="99.0.0.0"',
            },
            {
                'browser': 'Google Chrome 124.0.6367.118',
                'device_platform': 'macOS 14.4.1',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.1774.35',
            {
                'sec-ch-ua': '"Microsoft Edge";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-ch-ua-platform-version': '"14.4.1"',
                'sec-ch-ua-full-version-list': '"Microsoft Edge";v="113.0.1774.35", "Chromium";v="113.0.5672.63", "Not-A.Brand";v="24.0.0.0"',
            },
            {
                'browser': 'Microsoft Edge 113.0.1774.35',
                'device_platform': 'macOS 14.4.1',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            {
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'sec-ch-ua-platform-version': '"14.4.1"',
            },
            {
                'browser': 'Google Chrome 124',
                'device_platform': 'macOS 14.4.1',
                'mobile': False,
            },
        ),
        (
            'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
            {
                'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-model': '"Pixel 5"',
                'sec-ch-ua-platform': '"Android"',
                'sec-ch-ua-platform-version': '"13"',
            },
            {
                'browser': 'Google Chrome 124',
                'device_platform': 'Pixel 5 (Android 13)',
                'mobile': True,
            },
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
            None,
            {'browser': 'Safari 17.4.1', 'device_platform': 'macOS', 'mobile': False},
        ),
        (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            None,
            {'browser': 'Firefox 121.0', 'device_platform': 'macOS', 'mobile': False},
        ),
    ],
)
def test_user_agent_details(
    user_agent: str, client_hints: dict | None, output: dict
) -> None:
    assert (
        user_agent_details(
            cast(
                models.LoginSession,
                SimpleNamespace(
                    user_agent=user_agent, user_agent_client_hints=client_hints
                ),
            )
        )
        == output
    )
