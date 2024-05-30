"""Tests for pwned password validator integration (requires external web service)."""

import pytest
from requests_mock import Mocker

from funnel import models

from ...conftest import LoginFixtureProtocol, TestClient

# Sample password that will pass zxcvbn's complexity validation, but will be flagged
# by the pwned password validator
PWNED_PASSWORD = 'thisisone1'  # noqa: S105


@pytest.mark.flaky(reruns=2)  # Web service could fail occasionally
@pytest.mark.enable_socket
def test_pwned_password(
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    user_rincewind: models.User,
) -> None:
    """Pwned password validator will block attempt to use a compromised password."""
    login.as_(user_rincewind)
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
    assert rv.status_code == 200
    assert "This password was found in breached password lists" in rv.data.decode()


def test_pwned_password_mock_endpoint_down(
    requests_mock: Mocker,
    client: TestClient,
    csrf_token: str,
    login: LoginFixtureProtocol,
    user_rincewind: models.User,
) -> None:
    """If the pwned password API is not available, the password is allowed."""
    requests_mock.get('https://api.pwnedpasswords.com/range/1F074', status_code=404)
    login.as_(user_rincewind)

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
