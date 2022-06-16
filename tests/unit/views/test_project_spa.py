"""Test response types for project SPA endpoints."""

from typing import Optional
from urllib.parse import urlsplit

import pytest

# Endpoints to test within the project namespace
subpages = ['', 'updates', 'comments', 'sub', 'schedule', 'videos', 'crew']
# XHR header (without, with, with+accept)
xhr_headers = [
    None,
    {'X-Requested-With': 'xmlhttprequest'},
    {'X-Requested-With': 'xmlhttprequest', 'Accept': 'text/html, */*'},
]
# Logins (anon, promoter fixture)
login_sessions = [None, '_promoter_login']


@pytest.fixture()
def project_url(client, project_expo2010):
    """Relative URL for a project."""
    return urlsplit(project_expo2010.url_for()).path


@pytest.fixture()
def _promoter_login(login, user_vetinari):
    """Login as a project promoter."""
    login.as_(user_vetinari)


def test_project_url_is_as_expected(project_url):
    """Test the :func:`project_url` fixture before it's used in other tests."""
    # URL ends with '/'
    assert project_url.endswith('/')
    # URL is relative (for tests)
    assert project_url == '/ankh-morpork/2010/'


@pytest.mark.parametrize('page', subpages)
@pytest.mark.parametrize('xhr', xhr_headers)
@pytest.mark.parametrize('use_login', login_sessions)
def test_default_is_html(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    """Pages render as full HTML by default."""
    if use_login:
        request.getfixturevalue(use_login)
    headers = {}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize('page', subpages)
@pytest.mark.parametrize('xhr', xhr_headers)
@pytest.mark.parametrize('use_login', login_sessions)
def test_html_response(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    """Asking for a HTML page or a fragment (via XHR) returns a page or a fragment."""
    if use_login:
        request.getfixturevalue(use_login)
    headers = {}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize('page', subpages)
@pytest.mark.parametrize('use_login', login_sessions)
def test_json_response(
    request, client, use_login: Optional[str], project_url: str, page: str
):
    """Asking for JSON returns a JSON response."""
    if use_login:
        request.getfixturevalue(use_login)
    headers = {'Accept': 'application/json'}
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/json'
    assert 'status' in rv.json
    assert rv.json['status'] == 'ok'


@pytest.mark.parametrize('page', subpages)
@pytest.mark.parametrize('xhr', xhr_headers)
@pytest.mark.parametrize('use_login', login_sessions)
def test_htmljson_response(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    """Asking for HTML in JSON returns that as full HTML or a fragment."""
    if use_login:
        request.getfixturevalue(use_login)
    headers = {}
    if xhr:
        headers.update(xhr)
    headers['Accept'] = 'application/x.html+json'
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/x.html+json; charset=utf-8'
    assert 'status' in rv.json
    assert rv.json['status'] == 'ok'
    assert 'html' in rv.json
    assert bool(xhr) ^ rv.json['html'].startswith('<!DOCTYPE html>')
