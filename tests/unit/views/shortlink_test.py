"""Test shortlink views."""
# pylint: disable=redefined-outer-name

from collections.abc import Generator
from urllib.parse import urlsplit

import pytest
from flask.testing import FlaskClient

from funnel import models

from ...conftest import Flask, scoped_session


@pytest.fixture()
def shortlink_client(
    db_session: scoped_session, shortlinkapp: Flask
) -> Generator[FlaskClient, None, None]:
    """Provide a test client for shortlinkapp."""
    with shortlinkapp.test_client() as test_client:
        yield test_client


def test_shortlink_index(shortlink_client: FlaskClient) -> None:
    rv = shortlink_client.get('/')
    assert rv.status_code == 301
    assert urlsplit(rv.location).path == '/'


def test_shortlink_404(shortlink_client: FlaskClient) -> None:
    rv = shortlink_client.get('/example')
    assert rv.status_code == 404


@pytest.mark.dbcommit()
def test_shortlink_301(
    db_session: scoped_session, shortlink_client: FlaskClient
) -> None:
    db_session.add(models.Shortlink.new('https://example.com/', name='example'))
    db_session.commit()
    rv = shortlink_client.get('/example')
    assert rv.status_code == 301
    assert rv.location == 'https://example.com/'
    assert rv.content_security_policy == {'referrer': 'always'}
    assert rv.headers['Referrer-Policy'] == 'unsafe-url'


@pytest.mark.dbcommit()
def test_shortlink_410(
    db_session: scoped_session, shortlink_client: FlaskClient
) -> None:
    sl = models.Shortlink.new('https://example.com/', name='example')
    sl.enabled = False
    db_session.add(sl)
    db_session.commit()
    rv = shortlink_client.get('/example')
    assert rv.status_code == 410
