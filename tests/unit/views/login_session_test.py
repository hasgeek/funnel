"""Test login session helpers."""

import pytest
from flask import Flask, session

from funnel.views.login_session import save_session_next_url


@pytest.mark.parametrize(
    ('method', 'existing', 'nextarg', 'saved', 'result'),
    [
        ('GET', None, None, True, '/'),  # Default to index
        ('GET', None, '/new_next', True, '/new_next'),  # Use provided
        ('GET', '/existing_next', None, False, '/existing_next'),  # Use saved
        ('GET', '/existing_next', '/new_next', True, '/new_next'),  # Override saved
        ('POST', None, None, True, '/'),  # Default to index
        ('POST', None, '/new_next', True, '/new_next'),  # Use provided
        ('POST', '/existing_next', None, False, '/existing_next'),  # Use saved
        ('POST', '/existing_next', '/new_next', False, '/existing_next'),  # Use saved
    ],
)
def test_save_session_next_url(
    app: Flask,
    existing: str | None,
    method: str,
    nextarg: str | None,
    saved: bool,
    result: str,
) -> None:
    """Test if save_session_next_url() behaves appropriately."""
    test_url = f'/test_url?next={nextarg}' if nextarg else '/test_url'
    with app.test_request_context(path=test_url, method=method):
        if existing:
            session['next'] = existing
        else:
            session.pop('next', None)

        assert save_session_next_url() is saved
        assert session['next'] == result
