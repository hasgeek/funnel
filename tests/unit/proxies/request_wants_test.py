"""Tests for request_wants proxy."""
# pylint: disable=import-error,redefined-outer-name


from flask import Flask
import pytest

from funnel.proxies import init_app, request_wants
from funnel.proxies.request import RequestWants


@pytest.fixture()
def fixture_app() -> Flask:
    """Test app for testing Vary header in responses."""
    tapp = Flask(__name__)
    init_app(tapp)

    @tapp.route('/no-vary')
    def no_vary():  # skipcq: PTC-W0065
        return 'no-vary'

    @tapp.route('/fragment')
    def fragment():  # skipcq: PTC-W0065
        if request_wants.html_fragment:
            return '<p>HTML fragment</p>'
        return '<html><body><p>Full HTML</p></body></html>'

    @tapp.route('/json_or_html')
    def json_or_html():  # skipcq: PTC-W0065
        if request_wants.json:
            return {'status': 'ok'}
        return '<html><body><p>Status: ok</p></body></html>'

    return tapp


def test_request_wants_is_an_instance(
    request,
) -> None:
    """request_wants proxy is an instance of RequestWants class."""
    # pylint: disable=protected-access
    assert isinstance(request_wants._get_current_object(), RequestWants)
    app = request.getfixturevalue('app')
    with app.test_request_context():
        assert isinstance(request_wants._get_current_object(), RequestWants)
    # pylint: enable=protected-access

    # Falsy when there is no request context
    assert not request_wants
    # Truthy when there is a request context
    with app.test_request_context():
        assert request_wants


@pytest.mark.parametrize(
    ('accept_header', 'result'),
    [
        ('application/json', True),
        ('text/html', False),
        ('application/json;q=0.8, text/html;q=0.7', True),
        ('text/html;q=0.9, application/json;q=0.8', False),
        ('*/*', False),
    ],
)
def test_request_wants_json(app, accept_header, result) -> None:
    """Request wants a JSON response."""
    with app.test_request_context(headers={'Accept': accept_header}):
        assert request_wants.json is result
    # Without request context is always False
    assert request_wants.json is False


@pytest.mark.parametrize(
    ('xhr', 'accept_header', 'result'),
    [
        (True, 'application/json', False),
        (True, 'text/html', True),
        (True, 'text/x.fragment+html', True),
        (True, 'application/x.html+json', True),
        (True, '*/*', True),
        (False, 'application/json', False),
        (False, 'text/html', False),
        (False, 'text/x.fragment+html', True),
        (False, 'application/x.html+json', True),
        (False, '*/*', False),
    ],
)
def test_request_wants_html_fragment_xhr(app, xhr, accept_header, result) -> None:
    """Request wants a HTML fragment (XmlHttpRequest version)."""
    headers = {'Accept': accept_header}
    if xhr:
        headers['X-Requested-With'] = 'xmlhttprequest'
    with app.test_request_context(headers=headers):
        assert request_wants.html_fragment is result
    # Without request context is always False
    assert request_wants.html_fragment is False


@pytest.mark.parametrize(
    ('hx_request', 'accept_header', 'result'),
    [
        (True, 'application/json', False),
        (True, 'text/html', True),
        (True, 'text/x.fragment+html', True),
        (True, 'application/x.html+json', True),
        (True, '*/*', True),
        (True, None, True),
        (False, 'application/json', False),
        (False, 'text/html', False),
        (False, '*/*', False),
        (False, 'text/x.fragment+html', True),
        (False, 'application/x.html+json', True),
        (False, None, False),
    ],
)
def test_request_wants_html_fragment_htmx(
    app, hx_request, accept_header, result
) -> None:
    """Request wants a HTML fragment (HTMX version)."""
    # The Accept header is not a factor in HTMX calls.
    headers = {}
    if accept_header:
        headers['Accept'] = accept_header
    if hx_request:
        headers['HX-Request'] = 'true'
    with app.test_request_context(headers=headers):
        assert request_wants.html_fragment is result
    # Without request context is always False
    assert request_wants.html_fragment is False


@pytest.mark.parametrize(
    ('accept_header', 'result'),
    [
        ('application/json', False),
        ('application/x.html+json', True),
        ('*/*', False),
    ],
)
def test_request_wants_html_in_json(app, accept_header, result) -> None:
    """Request wants a HTML fragment embedded in a JSON response."""
    with app.test_request_context(headers={'Accept': accept_header}):
        assert request_wants.html_in_json is result
    # Without request context is always False
    assert request_wants.html_in_json is False


def test_request_wants_htmx(app) -> None:
    """Request wants a HTMX-compatible response."""
    with app.test_request_context():
        assert request_wants.htmx is False
    with app.test_request_context(headers={'HX-Request': 'true'}):
        assert request_wants.htmx is True


def test_response_varies(fixture_app) -> None:
    """Response Vary header is based on tests."""
    client = fixture_app.test_client()

    rv = client.get('/no-vary')
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert rv.headers.get('Vary', None) is None

    rv = client.get('/json_or_html')
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert rv.headers['Vary'] == 'Accept'

    rv = client.get('/json_or_html', headers={'Accept': 'application/json'})
    assert rv.status_code == 200
    assert rv.content_type == 'application/json'
    assert rv.headers['Vary'] == 'Accept'

    rv = client.get(
        '/fragment',
        headers={'Accept': 'text/html', 'X-Requested-With': 'XmlHttpRequest'},
    )
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert set(rv.headers['Vary'].split(', ')) == {
        'Accept',
        'X-Requested-With',
        'HX-Request',
    }
