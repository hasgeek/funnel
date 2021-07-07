"""
Tests for search views.

These tests verify the structure of the views, but don't actually test for whether the
views are returning expected results (at this time). Proper search testing requires a
corpus of searchable data in fixtures.
"""

from flask import url_for

import pytest

from funnel import app
from funnel.views.search import (
    Query,
    SearchInProfileProvider,
    SearchInProjectProvider,
    search_counts,
    search_providers,
)

search_all_types = list(search_providers.keys())
search_profile_types = [
    k for k, v in search_providers.items() if isinstance(v, SearchInProfileProvider)
]
search_project_types = [
    k for k, v in search_providers.items() if isinstance(v, SearchInProjectProvider)
]

# --- Tests for datatypes returned by search providers ---------------------------------


@pytest.mark.parametrize('stype', search_all_types)
def test_search_all_count_returns_int(stype, all_fixtures):
    """Assert that all_count() returns an int."""
    assert isinstance(search_providers[stype].all_count("test"), int)


@pytest.mark.parametrize('stype', search_profile_types)
def test_search_profile_count_returns_int(stype, org_ankhmorpork, all_fixtures):
    """Assert that profile_count() returns an int."""
    assert isinstance(
        search_providers[stype].profile_count("test", org_ankhmorpork.profile),
        int,
    )


@pytest.mark.parametrize('stype', search_project_types)
def test_search_project_count_returns_int(stype, project_expo2010, all_fixtures):
    """Assert that project_count() returns an int."""
    assert isinstance(
        search_providers[stype].profile_count("test", project_expo2010), int
    )


@pytest.mark.parametrize('stype', search_all_types)
def test_search_all_returns_query(stype, all_fixtures):
    """Assert that all_query() returns a query."""
    assert isinstance(search_providers[stype].all_query("test"), Query)


@pytest.mark.parametrize('stype', search_profile_types)
def test_search_profile_returns_query(stype, org_ankhmorpork, all_fixtures):
    """Assert that profile_query() returns a query."""
    assert isinstance(
        search_providers[stype].profile_query("test", org_ankhmorpork.profile),
        Query,
    )


@pytest.mark.parametrize('stype', search_project_types)
def test_search_project_returns_query(stype, project_expo2010, all_fixtures):
    """Assert that project_query() returns an int."""
    assert isinstance(
        search_providers[stype].project_query("test", project_expo2010), Query
    )


# --- Test search functions ------------------------------------------------------------


def test_search_counts(org_ankhmorpork, project_expo2010, all_fixtures):
    """Test that search_counts returns a list of dicts."""
    with app.test_request_context():
        r1 = search_counts("test")
        r2 = search_counts("test", profile=org_ankhmorpork.profile)
        r3 = search_counts("test", project=project_expo2010)

        for resultset in (r1, r2, r3):
            assert isinstance(resultset, list)
            for typeset in resultset:
                assert 'type' in typeset
                assert 'label' in typeset
                assert 'count' in typeset


# --- Test views -----------------------------------------------------------------------


def test_view_search_counts(client, org_ankhmorpork, project_expo2010, all_fixtures):
    """Search views return counts as a list of dicts."""
    org_ankhmorpork.profile.make_public()
    r1 = client.get(
        url_for('SearchView_search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()
    r2 = client.get(
        org_ankhmorpork.profile.url_for('search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()
    r3 = client.get(
        project_expo2010.url_for('search'),
        query_string={'q': "test"},
        headers={'Accept': 'application/json'},
    ).get_json()

    for resultset in (r1, r2, r3):
        assert isinstance(resultset, dict)
        assert 'counts' in resultset
        for countset in resultset['counts']:
            assert 'type' in countset
            assert 'label' in countset
            assert 'count' in countset


@pytest.mark.parametrize('stype', search_all_types)
def test_view_search_results_all(client, stype, all_fixtures):
    """Global search view returns results for each type."""
    resultset = client.get(
        url_for('SearchView_search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset


@pytest.mark.parametrize('stype', search_profile_types)
def test_view_search_results_profile(client, org_ankhmorpork, stype, all_fixtures):
    """Profile search view returns results for each type."""
    org_ankhmorpork.profile.make_public()
    resultset = client.get(
        org_ankhmorpork.profile.url_for('search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset


@pytest.mark.parametrize('stype', search_project_types)
def test_view_search_results_project(client, project_expo2010, stype, all_fixtures):
    """Project search view returns results for each type."""
    resultset = client.get(
        project_expo2010.url_for('search'),
        query_string={'q': "test", 'type': stype},
        headers={'Accept': 'application/json'},
    ).get_json()
    assert isinstance(resultset, dict)
    assert 'counts' in resultset
    for countset in resultset['counts']:
        assert 'type' in countset
        assert 'label' in countset
        assert 'count' in countset
    assert 'results' in resultset
