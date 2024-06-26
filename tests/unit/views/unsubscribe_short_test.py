"""Test for the unsubscribe short URL handler redirecting to main URL."""

from http import HTTPStatus
from secrets import token_urlsafe

from flask import Flask

RANDOM_TOKEN_MIN_LENGTH = 4


def test_unsubscribe_app_index(app: Flask, unsubscribeapp: Flask) -> None:
    """Unsubscribe app redirects from index to main app's notification preferences."""
    with unsubscribeapp.test_client() as client:
        rv = client.get('/')
        assert rv.status_code == HTTPStatus.MOVED_PERMANENTLY
    redirect_url: str = rv.location
    assert redirect_url.startswith(('http://', 'https://'))
    assert (
        app.url_for(
            'notification_preferences', utm_medium='sms', _anchor='sms', _external=True
        )
        == redirect_url
    )


def test_unsubscribe_app_url_redirect(app: Flask, unsubscribeapp: Flask) -> None:
    """Unsubscribe app does a simple redirect to main app's unsubscribe URL."""
    random_token = token_urlsafe(3)
    assert random_token is not None
    assert len(random_token) >= RANDOM_TOKEN_MIN_LENGTH
    with unsubscribeapp.test_client() as client:
        rv = client.get(f'/{random_token}')
        assert rv.status_code == HTTPStatus.MOVED_PERMANENTLY
    redirect_url: str = rv.location
    assert redirect_url.startswith(('http://', 'https://'))
    assert (
        app.url_for(
            'notification_unsubscribe_short', token=random_token, _external=True
        )
        == redirect_url
    )
