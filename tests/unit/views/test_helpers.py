from base64 import urlsafe_b64decode
from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlsplit

from flask import Flask
from werkzeug.routing import BuildError

from furl import furl
from pytz import utc
import pytest

from funnel import app
from funnel.views.helpers import (
    app_url_for,
    cleanurl_filter,
    compress,
    decompress,
    delete_cached_token,
    make_cached_token,
    retrieve_cached_token,
)


@pytest.fixture
def testapp():
    """Create a test app with an `index` view."""
    testapp = Flask(__name__)

    @testapp.route('/')
    def index():  # skipcq: PTC-W0065
        """Unused index view, only referred to via url_for."""
        return 'test_index'

    return testapp


class MockUrandom:
    """Mock for urandom."""

    def __init__(self, sequence):
        self.sequence = sequence
        self.counter = 0

    def __call__(self, length: int):
        value = self.sequence[self.counter % len(self.sequence)]
        self.counter += 1
        return value


def test_app_url_for(testapp):
    """Test that app_url_for works cross-app and in-app."""
    # App context is not necessary to use app_url_for
    url = app_url_for(app, 'index')
    assert url is not None

    # URLs are _external=True by default
    assert urlsplit(url).netloc not in ('', None)

    # URLs can be generated with _external=False although there's no good reason
    assert urlsplit(app_url_for(app, 'index', _external=False)).netloc == ''

    # Test cross-app
    with testapp.test_request_context():
        # app_url_for can be called for the app in context
        assert urlsplit(app_url_for(testapp, 'index')).path == '/'
        # Or for another app
        assert urlsplit(app_url_for(app, 'index')).path == '/'
        # Unfortunately we can't compare URLS in _this test_ as both paths are '/' and
        # server name comes from config. However, see next test:

    # A URL unavailable in one app can be available via another app
    with testapp.test_request_context():
        with pytest.raises(BuildError):
            app_url_for(testapp, 'change_password')
        change_password_url = app_url_for(app, 'change_password')
        assert change_password_url is not None

    # The same URL is returned when called with same-app context
    with app.test_request_context():
        change_password_url2 = app_url_for(app, 'change_password')
        assert change_password_url2 is not None
        assert change_password_url2 == change_password_url


def test_urlclean_filter():
    """The cleanurl filter produces compact browser-like URLs."""
    assert (
        cleanurl_filter(furl("https://example.com/some/path/?query=value"))
        == "example.com/some/path"
    )
    assert (
        cleanurl_filter(furl("example.com/some/path/?query=value"))
        == "example.com/some/path"
    )
    assert cleanurl_filter(furl("example.com/some/path/")) == "example.com/some/path"
    assert cleanurl_filter(furl("example.com/some/path")) == "example.com/some/path"
    assert cleanurl_filter(furl("example.com/")) == "example.com"
    assert cleanurl_filter(furl("//example.com/")) == "example.com"
    assert cleanurl_filter(furl("//test/")) == "test"
    assert cleanurl_filter(furl("foobar")) == "foobar"
    assert cleanurl_filter(furl("")) == ""

    assert (
        cleanurl_filter("https://example.com/some/path/?query=value")
        == "example.com/some/path"
    )
    assert (
        cleanurl_filter("example.com/some/path/?query=value") == "example.com/some/path"
    )
    assert cleanurl_filter("example.com/some/path/") == "example.com/some/path"
    assert cleanurl_filter("example.com/some/path") == "example.com/some/path"
    assert cleanurl_filter("example.com/") == "example.com"
    assert cleanurl_filter("//example.com/") == "example.com"
    assert cleanurl_filter("//test/") == "test"
    assert cleanurl_filter("foobar") == "foobar"
    assert cleanurl_filter("") == ""


def test_cached_token():
    """Test simplistic use of cached tokens (for SMS unsubscribe)."""
    test_payload = {
        'hello': 'world',
        'dt_aware': datetime(2010, 12, 15, tzinfo=utc),
        'dt_naive': datetime(2010, 12, 15),
    }
    token = make_cached_token(test_payload)
    assert token is not None
    return_payload = retrieve_cached_token(token)
    # The cache round-trips both naive and aware datetimes without a problem
    assert return_payload == test_payload
    delete_cached_token(token)
    assert retrieve_cached_token(token) is None


def test_cached_token_profanity_reuse():
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
        token = make_cached_token(test_payload)
        assert token == 'okay'
        # Profanity filter skipped the first candidate
        assert mockid.call_count == 2
        mockid.reset_mock()

        token = make_cached_token(test_payload)
        assert token == 'new0'
        # Dupe filter passed over the second 'okay'
        assert mockid.call_count == 2
        mockid.reset_mock()


def test_compress_decompress():
    """Test compress and decompress function on sample data."""
    # Compression is only effective on larger inputs, so the outputs here may be
    # larger than inputs.
    sample = b"This is a sample string to be compressed."
    for algorithm in ('gzip', 'deflate', 'br'):
        assert decompress(compress(sample, algorithm), algorithm) == sample
