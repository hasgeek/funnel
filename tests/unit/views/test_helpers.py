from urllib.parse import urlsplit

from flask import Flask
from werkzeug.routing import BuildError

from furl import furl
import pytest

from funnel import app
from funnel.views.helpers import app_url_for, cleanurl_filter


@pytest.fixture
def testapp():
    """Create a test app with an `index` view."""
    testapp = Flask(__name__)

    @testapp.route('/')
    def index():  # skipcq: PTC-W0065
        """Unused index view, only referred to via url_for."""
        return 'test_index'

    return testapp


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
