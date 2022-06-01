"""Test response types for project SPA endpoints."""

from itertools import product
from typing import Optional
from urllib.parse import urlsplit

import pytest

# Endpoints to test within the project namespace
subpages = ['', 'updates', 'comments', 'sub', 'schedule', 'videos', 'crew']
# XHR header (without, with)
xhr_headers = [None, {'X-Requested-With': 'xmlhttprequest'}]
# Logins (anon, promoter fixture)
login_sessions = [None, '_promoter_login']


@pytest.fixture()
def project_url(client, project_expo2010):
    return urlsplit(project_expo2010.url_for()).path


@pytest.fixture()
def _promoter_login(login, user_vetinari):
    login.as_(user_vetinari)


def test_project_url_is_as_expected(project_url):
    # URL ends with '/'
    assert project_url.endswith('/')
    # URL is relative (for tests)
    assert project_url == '/ankh-morpork/2010/'


@pytest.mark.parametrize(
    ('page', 'xhr', 'use_login'), product(subpages, xhr_headers, login_sessions)
)
def test_default_is_html(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    if use_login:
        request.getfixturevalue(use_login)
    headers = {}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize(
    ('page', 'xhr', 'use_login'), product(subpages, xhr_headers, login_sessions)
)
def test_html_response(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    if use_login:
        request.getfixturevalue(use_login)
    headers = {'Accept': 'text/html'}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize(('page', 'use_login'), product(subpages, login_sessions))
def test_json_response(
    request, client, use_login: Optional[str], project_url: str, page: str
):
    if use_login:
        request.getfixturevalue(use_login)
    headers = {'Accept': 'application/json'}
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/json'
    assert 'status' in rv.json
    assert rv.json['status'] == 'ok'


@pytest.mark.parametrize(
    ('page', 'xhr', 'use_login'), product(subpages, xhr_headers, login_sessions)
)
def test_htmljson_response(  # pylint: disable=too-many-arguments
    request,
    client,
    use_login: Optional[str],
    project_url: str,
    page: str,
    xhr: Optional[dict],
):
    if use_login:
        request.getfixturevalue(use_login)
    headers = {'Accept': 'application/x.html+json'}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/x.html+json; charset=utf-8'
    assert 'status' in rv.json
    assert rv.json['status'] == 'ok'
    assert 'html' in rv.json
    assert bool(xhr) ^ rv.json['html'].startswith('<!DOCTYPE html>')
