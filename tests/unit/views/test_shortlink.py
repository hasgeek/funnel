"""Test shortlink views."""

from urllib.parse import urlsplit

import pytest

from funnel import shortlinkapp
from funnel.models import Shortlink


@pytest.fixture()
def shortlink_client(db_session):
    """Provide a test client for shortlinkapp."""
    with shortlinkapp.test_client() as test_client:
        yield test_client


def test_shortlink_index(shortlink_client):
    rv = shortlink_client.get('/')
    assert rv.status_code == 301
    assert urlsplit(rv.location).path == '/'


def test_shortlink_404(shortlink_client):
    rv = shortlink_client.get('/example')
    assert rv.status_code == 404


def test_shortlink_301(db_session, shortlink_client):
    db_session.add(Shortlink.new('https://example.com/', name='example'))
    db_session.commit()
    rv = shortlink_client.get('/example')
    assert rv.status_code == 301
    assert rv.location == 'https://example.com/'
    assert rv.content_security_policy == {'referrer': 'always'}
    assert rv.headers['Referrer-Policy'] == 'unsafe-url'


def test_shortlink_410(db_session, shortlink_client):
    sl = Shortlink.new('https://example.com/', name='example')
    sl.enabled = False
    db_session.add(sl)
    db_session.commit()
    rv = shortlink_client.get('/example')
    assert rv.status_code == 410
