"""Tests for view helpers."""
# pylint: disable=redefined-outer-name

from base64 import urlsafe_b64decode
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from flask import Flask, request
from furl import furl
from werkzeug.routing import BuildError

import funnel.views.helpers as vhelpers


@pytest.fixture()
def testapp():
    """Create a test app with an `index` view."""
    new_app = Flask(__name__)

    @new_app.route('/')
    def index():  # skipcq: PTC-W0065
        """Unused index view, only referred to via url_for."""
        return 'test_index'

    return new_app


class MockUrandom:
    """Mock for urandom."""

    def __init__(self, sequence) -> None:
        self.sequence = sequence
        self.counter = 0

    def __call__(self, length: int) -> Any:
        value = self.sequence[self.counter % len(self.sequence)]
        self.counter += 1
        return value


def test_valid_timezones_remap() -> None:
    """Confirm valid_timezones has correct mappings for canary timezones."""
    assert 'asia/kolkata' in vhelpers.valid_timezones
    assert 'asia/calcutta' in vhelpers.valid_timezones
    assert vhelpers.valid_timezones['asia/kolkata'] == 'Asia/Kolkata'
    assert vhelpers.valid_timezones['asia/calcutta'] == 'Asia/Kolkata'


def test_app_url_for(app, testapp) -> None:
    """Test that app_url_for works cross-app and in-app."""
    # App context is not necessary to use app_url_for
    url = vhelpers.app_url_for(app, 'index')
    assert url is not None

    # URLs are _external=True by default
    assert urlsplit(url).netloc not in ('', None)

    # URLs can be generated with _external=False although there's no good reason
    assert urlsplit(vhelpers.app_url_for(app, 'index', _external=False)).netloc == ''

    # Test cross-app
    with testapp.test_request_context():
        # app_url_for can be called for the app in context
        assert urlsplit(vhelpers.app_url_for(testapp, 'index')).path == '/'
        # Or for another app
        assert urlsplit(vhelpers.app_url_for(app, 'index')).path == '/'
        # Unfortunately we can't compare URLS in _this test_ as both paths are '/' and
        # server name comes from config. However, see next test:

    # A URL unavailable in one app can be available via another app
    with testapp.test_request_context():
        with pytest.raises(BuildError):
            vhelpers.app_url_for(testapp, 'change_password')
        change_password_url = vhelpers.app_url_for(app, 'change_password')
        assert change_password_url is not None

    # The same URL is returned when called with same-app context
    with app.test_request_context():
        change_password_url2 = vhelpers.app_url_for(app, 'change_password')
        assert change_password_url2 is not None
        assert change_password_url2 == change_password_url


def test_validate_is_app_url(app) -> None:
    """Local URL validator compares a URL against the URL map."""
    with app.test_request_context():
        assert vhelpers.validate_is_app_url('/full/url/required') is False
        assert vhelpers.validate_is_app_url('https://example.com/') is False
        assert vhelpers.validate_is_app_url(f'//{request.host}/') is False
        assert vhelpers.validate_is_app_url(f'http://{request.host}/') is True
        assert (
            vhelpers.validate_is_app_url(
                f'http://{request.host}/this/does/not/exist/so/404'
            )
            is False
        )
        assert (
            vhelpers.validate_is_app_url(f'http://{request.host}/account/project')
            is True
        )
        assert (
            vhelpers.validate_is_app_url(f'http://{request.host}/account/project/')
            is True
        )
        assert (
            vhelpers.validate_is_app_url(f'http://{request.host}/~account/project/')
            is True
        )

    # TODO: This needs additional tests for an app with:
    # 1. No SERVER_NAME in config
    # 2. subdomain_matching enabled
    # 3. host_matching enabled


def test_urlclean_filter() -> None:
    """The cleanurl filter produces compact browser-like URLs."""
    assert (
        vhelpers.cleanurl_filter(furl("https://example.com/some/path/?query=value"))
        == "example.com/some/path"
    )
    assert (
        vhelpers.cleanurl_filter(furl("example.com/some/path/?query=value"))
        == "example.com/some/path"
    )
    assert (
        vhelpers.cleanurl_filter(furl("example.com/some/path/"))
        == "example.com/some/path"
    )
    assert (
        vhelpers.cleanurl_filter(furl("example.com/some/path"))
        == "example.com/some/path"
    )
    assert vhelpers.cleanurl_filter(furl("example.com/")) == "example.com"
    assert vhelpers.cleanurl_filter(furl("//example.com/")) == "example.com"
    assert vhelpers.cleanurl_filter(furl("//test/")) == "test"
    assert vhelpers.cleanurl_filter(furl("foobar")) == "foobar"
    assert vhelpers.cleanurl_filter(furl("")) == ""

    assert (
        vhelpers.cleanurl_filter("https://example.com/some/path/?query=value")
        == "example.com/some/path"
    )
    assert (
        vhelpers.cleanurl_filter("example.com/some/path/?query=value")
        == "example.com/some/path"
    )
    assert vhelpers.cleanurl_filter("example.com/some/path/") == "example.com/some/path"
    assert vhelpers.cleanurl_filter("example.com/some/path") == "example.com/some/path"
    assert vhelpers.cleanurl_filter("example.com/") == "example.com"
    assert vhelpers.cleanurl_filter("//example.com/") == "example.com"
    assert vhelpers.cleanurl_filter("//test/") == "test"
    assert vhelpers.cleanurl_filter("foobar") == "foobar"
    assert vhelpers.cleanurl_filter("") == ""


def test_cached_token() -> None:
    """Test simplistic use of cached tokens (for SMS unsubscribe)."""
    test_payload = {
        'hello': 'world',
        'dt_aware': datetime(2010, 12, 15, tzinfo=timezone.utc),
        'dt_naive': datetime(2010, 12, 15),
    }
    token = vhelpers.make_cached_token(test_payload)
    assert token is not None
    return_payload = vhelpers.retrieve_cached_token(token)
    # The cache round-trips both naive and aware datetimes without a problem
    assert return_payload == test_payload
    vhelpers.delete_cached_token(token)
    assert vhelpers.retrieve_cached_token(token) is None


def test_cached_token_profanity_reuse() -> None:
    """Test with a mock for the profanity filter and reuse filter in cached tokens."""
    mockids = MockUrandom(
        [
            urlsafe_b64decode(b'sexy'),
            urlsafe_b64decode(b'okay'),
            urlsafe_b64decode(b'okay'),
            urlsafe_b64decode(b'new0'),
        ]
    )
    test_payload = {'foo': 'bar'}
    with patch(
        'funnel.views.helpers.urandom',
        wraps=mockids,
    ) as mockid:
        token = vhelpers.make_cached_token(test_payload)
        assert token == 'okay'  # nosec
        # Profanity filter skipped the first candidate
        assert mockid.call_count == 2
        mockid.reset_mock()

        token = vhelpers.make_cached_token(test_payload)
        assert token == 'new0'  # nosec
        # Dupe filter passed over the second 'okay'
        assert mockid.call_count == 2
        mockid.reset_mock()


def test_compress_decompress() -> None:
    """Test compress and decompress function on sample data."""
    # Compression is only effective on larger inputs, so the outputs here may be
    # larger than inputs.
    sample = b"This is a sample string to be compressed."
    for algorithm in ('gzip', 'deflate', 'br'):
        assert (
            vhelpers.decompress(vhelpers.compress(sample, algorithm), algorithm)
            == sample
        )
