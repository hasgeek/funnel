"""Test response types for project SPA endpoints."""

from itertools import product
from urllib.parse import urlsplit

import pytest

# Endpoints to test within the project namespace
subpages = ['', 'updates', 'comments', 'sub', 'schedule', 'videos', 'crew']
# XHR header
xhr_headers = [{}, {'X-Requested-With': 'xmlhttprequest'}]


@pytest.fixture
def project_url(client, project_expo2010):
    return urlsplit(project_expo2010.url_for()).path


def test_project_url_is_as_expected(project_url):
    # URL ends with '/'
    assert project_url.endswith('/')
    # URL is relative (for tests)
    assert project_url == '/ankh-morpork/2010/'


@pytest.mark.parametrize(['page', 'xhr'], product(subpages, xhr_headers))
def test_default_is_html(client, project_url, page, xhr):
    headers = {}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize(['page', 'xhr'], product(subpages, xhr_headers))
def test_html_response(client, project_url, page, xhr):
    headers = {'Accept': 'text/html'}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'text/html; charset=utf-8'
    assert bool(xhr) ^ rv.data.decode('utf-8').startswith('<!DOCTYPE html>')


@pytest.mark.parametrize(['page', 'xhr'], product(subpages, xhr_headers))
def test_json_response(client, project_url, page, xhr):
    headers = {'Accept': 'application/json'}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/json'
    assert 'status' in rv.json and rv.json['status'] == 'ok'


@pytest.mark.parametrize(['page', 'xhr'], product(subpages, xhr_headers))
def test_htmljson_response(client, project_url, page, xhr):
    headers = {'Accept': 'application/x.html+json'}
    if xhr:
        headers.update(xhr)
    rv = client.get(project_url + page, headers=headers)
    assert rv.status_code == 200
    assert rv.content_type == 'application/x.html+json; charset=utf-8'
    assert 'status' in rv.json and rv.json['status'] == 'ok'
    assert 'html' in rv.json
    assert bool(xhr) ^ rv.json['html'].startswith('<!DOCTYPE html>')
